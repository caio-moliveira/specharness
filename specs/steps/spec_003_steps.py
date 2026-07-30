"""Step definitions da SPEC-003 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-003 --steps specs/steps/spec_003_steps.py`.
Tudo domínio puro: parser (`parse_spec`) e máquina de estados
(`can_transition`) do core, sem I/O.
"""

from __future__ import annotations

from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_core import SpecParseError, SpecStatus, can_transition, parse_spec

registry = StepRegistry()

_state: dict[str, Any] = {}

_VALID_SPEC = """---
spec: SPEC-042
title: "Spec de exemplo"
status: draft
type: feature
success_metrics:
  - "100% dos casos cobertos"
acceptance:
  - "um critério"
---

## Contexto

corpo da spec
"""

_TWO_GHERKIN_BLOCKS = (
    _VALID_SPEC
    + """
```gherkin
# language: pt
Funcionalidade: a

  Cenário: um
    Quando algo acontece
    Então algo é observado
```

texto entre blocos

```gherkin
# language: pt
Funcionalidade: b

  Cenário: dois
    Quando outra coisa acontece
    Então outra coisa é observada
```
"""
)


@registry.step(r"um arquivo markdown com frontmatter YAML válido e id \"SPEC-042\"")
def _given_valid_doc() -> None:
    _state["doc"] = _VALID_SPEC


@registry.step(r"um arquivo markdown sem bloco de frontmatter")
def _given_no_frontmatter() -> None:
    _state["doc"] = "# só markdown\n\nsem frontmatter aqui\n"


@registry.step(r"um arquivo markdown cujo frontmatter tem YAML sintaticamente inválido")
def _given_broken_yaml() -> None:
    _state["doc"] = "---\nspec: [SPEC-042\n---\n\ncorpo\n"


@registry.step(r"um arquivo markdown com id \"SPEC42\" no frontmatter")
def _given_bad_id() -> None:
    _state["doc"] = _VALID_SPEC.replace("spec: SPEC-042", "spec: SPEC42")


@registry.step(r"uma spec cujo corpo contém dois blocos cercados gherkin")
def _given_two_blocks() -> None:
    _state["doc"] = _TWO_GHERKIN_BLOCKS


@registry.step(r"o parser processa o arquivo")
def _when_parse() -> None:
    _state["parsed"] = _state["error"] = None
    try:
        _state["parsed"] = parse_spec(_state["doc"])
    except SpecParseError as exc:
        _state["error"] = exc


@registry.step(r"o resultado expõe id, status, métricas de sucesso e corpo tipados")
def _then_typed_result() -> None:
    parsed = _state["parsed"]
    assert parsed is not None, _state["error"]
    assert parsed.spec_id == "SPEC-042"
    assert isinstance(parsed.frontmatter.status, SpecStatus)
    assert parsed.frontmatter.success_metrics == ["100% dos casos cobertos"]
    assert "corpo da spec" in parsed.body


def _assert_error_mentions(needle: str) -> None:
    error = _state["error"]
    assert error is not None, f"esperava SpecParseError, veio {_state['parsed']!r}"
    assert needle in str(error), str(error)


@registry.step(r"uma SpecParseError é lançada mencionando \"frontmatter\"")
def _then_error_frontmatter() -> None:
    _assert_error_mentions("frontmatter")


@registry.step(r"uma SpecParseError é lançada mencionando \"YAML\"")
def _then_error_yaml() -> None:
    _assert_error_mentions("YAML")


@registry.step(r"uma SpecParseError é lançada mencionando \"invalid spec id\"")
def _then_error_bad_id() -> None:
    _assert_error_mentions("invalid spec id")


@registry.step(r"uma spec no status \"approved\"")
def _given_status_approved() -> None:
    _state["from"] = SpecStatus.APPROVED


@registry.step(r"uma spec no status \"verifying\"")
def _given_status_verifying() -> None:
    _state["from"] = SpecStatus.VERIFYING


@registry.step(r"o sistema tenta mover direto para \"in_progress\"")
def _when_skip_gate() -> None:
    _state["allowed"] = can_transition(_state["from"], SpecStatus.IN_PROGRESS)


@registry.step(r"o sistema tenta mover para \"in_progress\"")
def _when_rollback() -> None:
    _state["allowed"] = can_transition(_state["from"], SpecStatus.IN_PROGRESS)


@registry.step(r"a transição é rejeitada pela máquina de estados")
def _then_rejected() -> None:
    assert _state["allowed"] is False


@registry.step(r"a transição é aceita pela máquina de estados")
def _then_accepted() -> None:
    assert _state["allowed"] is True


@registry.step(r"exatamente dois blocos gherkin são disponibilizados para o gate")
def _then_two_gherkin_blocks() -> None:
    parsed = _state["parsed"]
    assert parsed is not None, _state["error"]
    assert len(parsed.gherkin_blocks) == 2, parsed.gherkin_blocks
