"""The deterministic Readiness Gate (SPEC-010, SPEC-001 §8.1).

The mechanical floor of the Definition of Ready: everything checkable without an
LLM runs here, fast and free (< 500ms). It mirrors the `readiness-review` skill's
deterministic layer exactly — a divergence between the two is a bug in one of
them. The LLM layer (SPEC-011) only sees specs that pass here.

Pure domain (ADR-001): the caller reads the spec and builds the registry; this
module decides. Output is structured into blockers and recommendations, each with
a location, plus the criterion x scenario matrix.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from .gherkin import Feature, Scenario, parse_feature
from .specschema import ParsedSpec, SpecStatus

#: The canonical ambiguous-term list (readiness-review skill; SPEC-001 §8.1).
AMBIGUOUS_TERMS: tuple[str, ...] = ("rápido", "adequado", "amigável", "fácil", "intuitivo")

BLOCKER = "blocker"
RECOMMENDATION = "recommendation"

# Filler that carries no coverage signal: pt-BR stopwords, Gherkin keywords and a
# few domain words common to nearly every criterion/scenario.
_STOPWORDS = frozenset(
    {
        "para",
        "como",
        "cada",
        "pela",
        "pelo",
        "sobre",
        "entre",
        "quando",
        "dado",
        "então",
        "entao",
        "funcionalidade",
        "cenário",
        "cenario",
        "spec",
        "specs",
        "deve",
        "será",
        "está",
        "estão",
        "sem",
        "com",
        "dos",
        "das",
        "uma",
        "que",
        "este",
        "esta",
        "esse",
        "essa",
        "isso",
        "aqui",
        "onde",
        "seu",
        "sua",
        "seus",
        "suas",
        "nao",
        "não",
    }
)
_TOKEN_RE = re.compile(r"[0-9a-zà-ÿ]+")


@dataclass(frozen=True)
class Finding:
    """One gate result, structured for the report (critério A6)."""

    kind: str  # BLOCKER | RECOMMENDATION
    message: str
    location: str
    suggestion: str | None = None


@dataclass(frozen=True)
class CoverageRow:
    """A criterion and the scenarios (1-based indices) that mechanically cover it."""

    index: int
    criterion: str
    covered_by: tuple[int, ...]

    @property
    def covered(self) -> bool:
        return bool(self.covered_by)


@dataclass(frozen=True)
class ReadinessReport:
    findings: tuple[Finding, ...]
    matrix: tuple[CoverageRow, ...]

    @property
    def blockers(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind == BLOCKER)

    @property
    def recommendations(self) -> tuple[Finding, ...]:
        return tuple(f for f in self.findings if f.kind == RECOMMENDATION)

    @property
    def passed(self) -> bool:
        return not self.blockers


def evaluate_readiness(spec: ParsedSpec, registry: Mapping[str, SpecStatus]) -> ReadinessReport:
    """Run every deterministic Definition-of-Ready check over one spec."""
    fm = spec.frontmatter
    features = [parse_feature(block) for block in spec.gherkin_blocks]
    scenarios = [scenario for feature in features for scenario in feature.scenarios]

    findings: list[Finding] = []
    findings += _check_acceptance_and_scenarios(fm.acceptance, scenarios)
    matrix = _coverage_matrix(fm.acceptance, scenarios)
    findings += _check_coverage(matrix)
    findings += _check_metrics(fm.success_metrics)
    findings += _check_dependencies(fm.depends_on, registry)
    findings += _lint_bdd(features, scenarios)

    return ReadinessReport(findings=tuple(findings), matrix=tuple(matrix))


# --- A1: critérios e cenários ----------------------------------------------


def _check_acceptance_and_scenarios(
    acceptance: list[str], scenarios: list[Scenario]
) -> list[Finding]:
    findings: list[Finding] = []
    if not acceptance:
        findings.append(Finding(BLOCKER, "spec sem critérios de aceite", "frontmatter.acceptance"))
    if not scenarios:
        findings.append(
            Finding(BLOCKER, "spec sem cenários Gherkin parseáveis", "body (bloco ```gherkin)")
        )
    return findings


# --- A2: matriz critério x cenário -----------------------------------------


def _coverage_matrix(acceptance: list[str], scenarios: list[Scenario]) -> list[CoverageRow]:
    scenario_tokens = [_tokens(f"{s.title} {s.step_text}") for s in scenarios]
    rows: list[CoverageRow] = []
    for index, criterion in enumerate(acceptance, start=1):
        criterion_tokens = _tokens(criterion)
        covered_by = tuple(
            j for j, tokens in enumerate(scenario_tokens, start=1) if criterion_tokens & tokens
        )
        rows.append(CoverageRow(index=index, criterion=criterion, covered_by=covered_by))
    return rows


def _check_coverage(matrix: list[CoverageRow]) -> list[Finding]:
    return [
        Finding(
            BLOCKER,
            f"critério de aceite sem cenário que o cubra: {row.criterion!r}",
            f"acceptance[{row.index}]",
        )
        for row in matrix
        if not row.covered
    ]


# --- A3: métricas -----------------------------------------------------------


def _check_metrics(metrics: list[str]) -> list[Finding]:
    if not metrics:
        return [Finding(BLOCKER, "spec sem success_metrics", "frontmatter.success_metrics")]
    findings: list[Finding] = []
    if not any(_is_measurable(m) for m in metrics):
        findings.append(
            Finding(
                BLOCKER,
                "nenhuma success_metric é mensurável sintaticamente",
                "frontmatter.success_metrics",
            )
        )
    for index, metric in enumerate(metrics, start=1):
        if not _is_measurable(metric):
            findings.append(
                Finding(
                    RECOMMENDATION,
                    f"métrica não-mensurável sintaticamente: {metric!r}",
                    f"success_metrics[{index}]",
                    suggestion="inclua um número, unidade ou comparador (< 500ms, 100%, 0)",
                )
            )
    return findings


# --- A4: dependências -------------------------------------------------------


def _check_dependencies(depends_on: list[str], registry: Mapping[str, SpecStatus]) -> list[Finding]:
    findings: list[Finding] = []
    for dep in depends_on:
        status = registry.get(dep)
        if status is None:
            findings.append(
                Finding(
                    BLOCKER, f"depends_on referencia spec inexistente: {dep}", f"depends_on:{dep}"
                )
            )
        elif status == SpecStatus.ARCHIVED:
            findings.append(
                Finding(
                    BLOCKER,
                    f"depends_on referencia spec archived (congelada): {dep}",
                    f"depends_on:{dep}",
                )
            )
    return findings


# --- A5: lint de BDD --------------------------------------------------------


def _lint_bdd(features: list[Feature], scenarios: list[Scenario]) -> list[Finding]:
    findings: list[Finding] = []
    for feature in features:
        if feature.language != "pt":
            findings.append(
                Finding(
                    RECOMMENDATION,
                    "bloco Gherkin sem '# language: pt'",
                    "body (bloco ```gherkin)",
                    suggestion="adicione '# language: pt' no topo do bloco",
                )
            )
    for index, scenario in enumerate(scenarios, start=1):
        when_count = len(scenario.when_steps)
        if when_count != 1:
            findings.append(
                Finding(
                    RECOMMENDATION,
                    f"cenário tem {when_count} passos 'Quando' (esperado exatamente 1)",
                    f"cenário {index}: {scenario.title!r}",
                )
            )
        haystack = f"{scenario.title} {scenario.step_text}"
        for term in AMBIGUOUS_TERMS:
            if _contains_term(haystack, term):
                findings.append(
                    Finding(
                        RECOMMENDATION,
                        f"termo ambíguo {term!r} no cenário {index}",
                        f"cenário {index}: {scenario.title!r}",
                        suggestion=f"troque {term!r} por um critério mensurável",
                    )
                )
    return findings


# --- helpers ----------------------------------------------------------------


def _tokens(text: str) -> set[str]:
    return {w for w in _TOKEN_RE.findall(text.lower()) if len(w) >= 4 and w not in _STOPWORDS}


def _is_measurable(metric: str) -> bool:
    return bool(re.search(r"\d", metric)) or any(sym in metric for sym in "<>%≤≥")


def _contains_term(text: str, term: str) -> bool:
    return re.search(rf"\b{re.escape(term)}\b", text, re.IGNORECASE) is not None
