"""The minimal BDD runner (SPEC-012, ADR-018)."""

from __future__ import annotations

import pytest
from specharness_adapters.verify import (
    StepRegistry,
    VerifyError,
    load_steps,
    run_scenario,
    run_spec,
)
from specharness_core import parse_spec
from specharness_core.gherkin import Scenario, Step


def _scenario(step_texts):
    return Scenario(title="c", steps=tuple(Step("Quando", text) for text in step_texts))


def test_passed_when_every_step_matches_and_passes():
    registry = StepRegistry()
    registry.register("faz algo", lambda: None)

    assert run_scenario(_scenario(["faz algo"]), registry) == "passed"


def test_pending_when_a_step_has_no_definition():
    assert run_scenario(_scenario(["passo sem definição"]), StepRegistry()) == "pending"


def test_failed_when_a_step_raises():
    registry = StepRegistry()

    def boom():
        raise AssertionError("não bate")

    registry.register("explode", boom)

    assert run_scenario(_scenario(["explode"]), registry) == "failed"


def test_a_scenario_without_steps_is_pending():
    assert run_scenario(Scenario("vazio", ()), StepRegistry()) == "pending"


def test_the_decorator_registers_a_step():
    registry = StepRegistry()

    @registry.step("olá")
    def _greet():
        pass

    assert registry.find("olá mundo") is not None
    assert registry.find("tchau") is None


_SPEC = """---
spec: SPEC-042
title: "T"
status: verifying
type: feature
success_metrics: ["m < 1s"]
acceptance: ["a"]
---

```gherkin
# language: pt
Funcionalidade: x

  Cenário: primeiro
    Quando alpha
    Então beta

  Cenário: segundo
    Quando gamma
    Então delta
```
"""


def test_run_spec_iterates_every_scenario():
    registry = StepRegistry()
    registry.register(".+", lambda: None)  # casa qualquer passo

    results = run_spec(parse_spec(_SPEC), registry)

    assert [title for title, _ in results] == ["primeiro", "segundo"]
    assert all(status == "passed" for _, status in results)


# --- loader -----------------------------------------------------------------


def test_load_steps_reads_a_registry_module(tmp_path):
    module = tmp_path / "steps.py"
    module.write_text(
        "from specharness_adapters.verify import StepRegistry\n"
        "registry = StepRegistry()\n\n"
        "@registry.step('faz algo')\n"
        "def _():\n    pass\n",
        encoding="utf-8",
    )

    registry = load_steps(module)

    assert registry.find("faz algo") is not None


def test_load_steps_without_a_registry_raises(tmp_path):
    module = tmp_path / "bad.py"
    module.write_text("x = 1\n", encoding="utf-8")

    with pytest.raises(VerifyError):
        load_steps(module)


def test_load_steps_that_fails_to_import_raises(tmp_path):
    module = tmp_path / "broken.py"
    module.write_text("import um_modulo_que_nao_existe\n", encoding="utf-8")

    with pytest.raises(VerifyError):
        load_steps(module)
