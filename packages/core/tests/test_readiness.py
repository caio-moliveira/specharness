"""The deterministic Readiness Gate (SPEC-010, todos os critérios + métricas)."""

from __future__ import annotations

import time

import pytest
from specharness_core import AMBIGUOUS_TERMS, SpecStatus, evaluate_readiness
from specharness_core.readiness import BLOCKER
from specharness_core.specschema import ParsedSpec, SpecFrontmatter

_GOOD_GHERKIN = """## Cenários

```gherkin
# language: pt
Funcionalidade: linking

  Cenário: trailer válido vincula
    Dado um commit com trailer
    Quando o track roda
    Então o commit é vinculado à spec

  Cenário: commit sem trailer é órfão
    Dado um commit sem trailer
    Quando o track roda
    Então o commit entra na métrica de órfãos
```
"""

_REGISTRY = {"SPEC-003": SpecStatus.READY}


def _spec(*, acceptance=None, metrics=None, depends_on=None, body=_GOOD_GHERKIN):
    fm = SpecFrontmatter(
        spec="SPEC-042",
        title="T",
        status=SpecStatus.APPROVED,
        acceptance=[
            "Commit com trailer válido é vinculado à spec",
            "Commit sem trailer entra na métrica de órfãos",
        ]
        if acceptance is None
        else acceptance,
        success_metrics=["linking em < 500ms", "0 falso-positivos"] if metrics is None else metrics,
        depends_on=["SPEC-003"] if depends_on is None else depends_on,
    )
    return ParsedSpec(frontmatter=fm, body=body)


# --- cenário 1: spec completa passa no piso (métrica 2: sem falso-positivo) --


def test_a_complete_spec_passes_without_blockers():
    report = evaluate_readiness(_spec(), _REGISTRY)

    assert report.passed is True
    assert report.blockers == ()
    assert report.recommendations == ()


# --- critério A1 ------------------------------------------------------------


def test_a_spec_without_acceptance_does_not_pass():
    report = evaluate_readiness(_spec(acceptance=[]), _REGISTRY)

    assert report.passed is False
    assert any("critérios de aceite" in b.message for b in report.blockers)


def test_a_spec_without_parseable_scenarios_does_not_pass():
    report = evaluate_readiness(_spec(body="## Sem gherkin\n\ntexto\n"), _REGISTRY)

    assert report.passed is False
    assert any("cenários Gherkin" in b.message for b in report.blockers)


# --- critério A2: matriz critério x cenário ---------------------------------


def test_an_uncovered_criterion_is_a_blocker_pointing_at_the_criterion():
    report = evaluate_readiness(
        _spec(
            acceptance=[
                "Commit com trailer válido é vinculado à spec",
                "O relatório é exportado em PDF assinado",  # nenhum cenário cobre
            ]
        ),
        _REGISTRY,
    )

    assert report.passed is False
    uncovered = [b for b in report.blockers if "sem cenário que o cubra" in b.message]
    assert len(uncovered) == 1
    assert uncovered[0].location == "acceptance[2]"
    # a matriz mostra o critério 1 coberto e o 2 descoberto
    assert report.matrix[0].covered is True
    assert report.matrix[1].covered is False


# --- critério A3: métricas --------------------------------------------------


def test_missing_metrics_is_a_blocker():
    report = evaluate_readiness(_spec(metrics=[]), _REGISTRY)

    assert any("sem success_metrics" in b.message for b in report.blockers)


def test_a_non_measurable_metric_is_a_recommendation():
    report = evaluate_readiness(
        _spec(metrics=["linking em < 500ms", "a experiência deve ser agradável"]), _REGISTRY
    )

    assert report.passed is True  # há uma métrica mensurável, então não bloqueia
    assert any("não-mensurável" in r.message for r in report.recommendations)


def test_all_metrics_non_measurable_is_a_blocker():
    report = evaluate_readiness(_spec(metrics=["deve ser agradável", "deve ser bonito"]), _REGISTRY)

    assert report.passed is False
    assert any("nenhuma success_metric é mensurável" in b.message for b in report.blockers)


# --- critério A4: dependências ----------------------------------------------


def test_a_nonexistent_dependency_blocks():
    report = evaluate_readiness(_spec(depends_on=["SPEC-999"]), {})

    assert report.passed is False
    assert any("inexistente" in b.message and "SPEC-999" in b.message for b in report.blockers)


def test_an_archived_dependency_blocks():
    report = evaluate_readiness(_spec(depends_on=["SPEC-003"]), {"SPEC-003": SpecStatus.ARCHIVED})

    assert report.passed is False
    assert any("archived" in b.message for b in report.blockers)


# --- critério A5: lint de BDD -----------------------------------------------


@pytest.mark.parametrize("term", AMBIGUOUS_TERMS)
def test_every_canonical_ambiguous_term_is_detected(term):
    body = (
        "## Cenários\n\n```gherkin\n# language: pt\nFuncionalidade: x\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        f"    Então o commit é vinculado de forma {term}\n"
        "  Cenário: commit sem trailer é órfão\n"
        "    Dado um commit sem trailer\n"
        "    Quando o track roda\n"
        "    Então o commit entra na métrica de órfãos\n```\n"
    )

    report = evaluate_readiness(_spec(body=body), _REGISTRY)

    assert any(term in r.message and "ambíguo" in r.message for r in report.recommendations)


def test_two_when_steps_in_a_scenario_is_a_recommendation():
    body = (
        "## Cenários\n\n```gherkin\n# language: pt\nFuncionalidade: x\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        "    Quando roda de novo\n"
        "    Então o commit é vinculado à spec\n"
        "  Cenário: commit sem trailer é órfão\n"
        "    Dado um commit sem trailer\n"
        "    Quando o track roda\n"
        "    Então o commit entra na métrica de órfãos\n```\n"
    )

    report = evaluate_readiness(_spec(body=body), _REGISTRY)

    assert any("Quando" in r.message for r in report.recommendations)


def test_missing_language_pt_is_a_recommendation():
    body = _GOOD_GHERKIN.replace("# language: pt\n", "")

    report = evaluate_readiness(_spec(body=body), _REGISTRY)

    assert any("language: pt" in r.message for r in report.recommendations)


# --- critério A6 + métrica 1 ------------------------------------------------


def test_findings_are_structured_with_location():
    report = evaluate_readiness(_spec(acceptance=[]), _REGISTRY)

    for finding in report.findings:
        assert finding.kind in (BLOCKER, "recommendation")
        assert finding.location


def test_the_gate_runs_well_under_the_budget():
    spec = _spec()

    started = time.perf_counter()
    for _ in range(50):
        evaluate_readiness(spec, _REGISTRY)
    per_spec = (time.perf_counter() - started) / 50

    assert per_spec < 0.5  # métrica 1: < 500ms por spec
