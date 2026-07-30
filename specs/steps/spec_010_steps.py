"""Step definitions da SPEC-010 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-010 --steps specs/steps/spec_010_steps.py`.
Exercita o piso determinístico do Readiness Gate (`evaluate_readiness`, core
puro) com specs sintéticas construídas para disparar cada checagem.
"""

from __future__ import annotations

from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_core import SpecStatus, evaluate_readiness, parse_spec

registry = StepRegistry()

_state: dict[str, Any] = {}


def _spec_doc(
    *,
    acceptance: list[str],
    metrics: list[str],
    gherkin: str,
    depends_on: list[str] | None = None,
) -> str:
    def _yaml_list(items: list[str]) -> str:
        return "[" + ", ".join(f'"{item}"' for item in items) + "]"

    depends = _yaml_list(depends_on or [])
    return (
        "---\n"
        "spec: SPEC-042\n"
        'title: "Spec sintética"\n'
        "status: draft\n"
        "type: feature\n"
        f"depends_on: {depends}\n"
        f"success_metrics: {_yaml_list(metrics)}\n"
        f"acceptance: {_yaml_list(acceptance)}\n"
        "---\n\n## Contexto\n\ncorpo\n\n" + gherkin
    )


_COVERING_GHERKIN = """```gherkin
# language: pt
Funcionalidade: listagem

  Cenário: total de vínculos é listado
    Dado commits processados
    Quando o comando roda
    Então a saída lista o total de vínculos válidos
```
"""


@registry.step(r"uma spec com critérios, cenários que os cobrem e métricas mensuráveis")
def _given_complete_spec() -> None:
    _state["doc"] = _spec_doc(
        acceptance=["a saída lista o total de vínculos válidos"],
        metrics=["100% dos vínculos listados"],
        gherkin=_COVERING_GHERKIN,
    )
    _state["registry"] = {}


@registry.step(r"uma spec sem critérios de aceite ou sem cenários Gherkin parseáveis")
def _given_spec_without_acceptance() -> None:
    _state["doc"] = _spec_doc(
        acceptance=[],
        metrics=["100% dos vínculos listados"],
        gherkin=_COVERING_GHERKIN,
    )
    _state["registry"] = {}


@registry.step(r"uma spec cujo segundo critério de aceite não tem cenário correspondente")
def _given_uncovered_second_criterion() -> None:
    _state["doc"] = _spec_doc(
        acceptance=[
            "a saída lista o total de vínculos válidos",
            "o relatório exporta imagens vetoriais imprimíveis",
        ],
        metrics=["100% dos vínculos listados"],
        gherkin=_COVERING_GHERKIN,
    )
    _state["registry"] = {}


@registry.step(r"uma spec com uma success_metric sem número, unidade ou comparador")
def _given_unmeasurable_metric() -> None:
    _state["doc"] = _spec_doc(
        acceptance=["a saída lista o total de vínculos válidos"],
        metrics=["100% dos vínculos listados", "o resultado agrada o time"],
        gherkin=_COVERING_GHERKIN,
    )
    _state["registry"] = {}


@registry.step(r"um cenário contendo o termo \"rápido\" em um Então")
def _given_ambiguous_term() -> None:
    gherkin = _COVERING_GHERKIN.replace(
        "Então a saída lista o total de vínculos válidos",
        "Então a saída lista o total de vínculos válidos e o comando é rápido",
    )
    _state["doc"] = _spec_doc(
        acceptance=["a saída lista o total de vínculos válidos"],
        metrics=["100% dos vínculos listados"],
        gherkin=gherkin,
    )
    _state["registry"] = {}


@registry.step(r"uma spec cujo depends_on referencia uma spec archived")
def _given_archived_dependency() -> None:
    _state["doc"] = _spec_doc(
        acceptance=["a saída lista o total de vínculos válidos"],
        metrics=["100% dos vínculos listados"],
        gherkin=_COVERING_GHERKIN,
        depends_on=["SPEC-001"],
    )
    _state["registry"] = {"SPEC-001": SpecStatus.ARCHIVED}


@registry.step(r"o gate determinístico executa")
def _when_gate_runs() -> None:
    _state["report"] = evaluate_readiness(parse_spec(_state["doc"]), _state["registry"])


@registry.step(r"o resultado é aprovado sem bloqueadores")
def _then_passes_clean() -> None:
    report = _state["report"]
    assert report.passed, [f.message for f in report.blockers]
    assert not report.blockers


@registry.step(r"o resultado tem um bloqueador e não passa")
def _then_blocked() -> None:
    report = _state["report"]
    assert not report.passed
    assert any("critérios de aceite" in f.message for f in report.blockers), [
        f.message for f in report.blockers
    ]


@registry.step(r"o bloqueador aponta o critério descoberto na matriz critério x cenário")
def _then_uncovered_criterion_located() -> None:
    report = _state["report"]
    blocker = next((f for f in report.blockers if "sem cenário que o cubra" in f.message), None)
    assert blocker is not None, [f.message for f in report.blockers]
    assert blocker.location == "acceptance[2]", blocker.location
    assert not report.matrix[1].covered  # a linha 2 da matriz está descoberta


@registry.step(r"a métrica não-mensurável é reportada com sua localização")
def _then_unmeasurable_metric_located() -> None:
    report = _state["report"]
    finding = next((f for f in report.findings if "métrica não-mensurável" in f.message), None)
    assert finding is not None, [f.message for f in report.findings]
    assert finding.location == "success_metrics[2]", finding.location


@registry.step(r"o lint reporta o termo ambíguo com sugestão de torná-lo mensurável")
def _then_ambiguous_term_reported() -> None:
    report = _state["report"]
    finding = next((f for f in report.findings if "termo ambíguo 'rápido'" in f.message), None)
    assert finding is not None, [f.message for f in report.findings]
    assert finding.suggestion is not None and "mensurável" in finding.suggestion


@registry.step(r"o bloqueador indica a dependência congelada")
def _then_archived_dependency_blocked() -> None:
    report = _state["report"]
    assert any("congelada" in f.message and "SPEC-001" in f.message for f in report.blockers), [
        f.message for f in report.blockers
    ]
