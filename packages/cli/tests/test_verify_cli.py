"""`specharness verify <spec>` — BDD gate de done (SPEC-012)."""

from __future__ import annotations

import json

import pytest
from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()

_SPEC = """---
spec: SPEC-042
title: "T"
status: verifying
type: feature
owner: caio
created: 2026-07-25
success_metrics: ["m < 1s"]
acceptance: ["a"]
---

## Cenários

```gherkin
# language: pt
Funcionalidade: linking

  Cenário: trailer válido vincula
    Dado um commit com trailer
    Quando o track roda
    Então o commit é vinculado à spec
```
"""

_MATCHING_STEPS = (
    "from specharness_adapters.verify import StepRegistry\n"
    "registry = StepRegistry()\n\n"
    "@registry.step('.+')\n"
    "def _ok():\n    pass\n"
)

_FAILING_STEPS = (
    "from specharness_adapters.verify import StepRegistry\n"
    "registry = StepRegistry()\n\n"
    "@registry.step('.+')\n"
    "def _boom():\n    raise AssertionError('vermelho')\n"
)


@pytest.fixture(autouse=True)
def in_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "SPEC-042-x.md").write_text(_SPEC, "utf-8")
    return tmp_path


def _steps_file(tmp_path, body):
    path = tmp_path / "steps.py"
    path.write_text(body, "utf-8")
    return str(path)


def test_no_steps_makes_scenarios_pending_and_blocks(in_repo):
    result = runner.invoke(app, ["verify", "SPEC-042"])

    assert result.exit_code == 1
    assert "pendente" in result.output.lower()
    assert "done bloqueado" in result.output.lower()


def test_matching_steps_pass_and_release(in_repo):
    result = runner.invoke(
        app, ["verify", "SPEC-042", "--steps", _steps_file(in_repo, _MATCHING_STEPS)]
    )

    assert result.exit_code == 0, result.output
    assert "verdes" in result.output.lower()


def test_failing_step_blocks_and_names_the_scenario(in_repo):
    result = runner.invoke(
        app, ["verify", "SPEC-042", "--steps", _steps_file(in_repo, _FAILING_STEPS)]
    )

    assert result.exit_code == 1
    assert "falhou" in result.output.lower()
    assert "trailer válido vincula" in result.output


def test_json_mode_is_machine_readable(in_repo):
    result = runner.invoke(
        app, ["verify", "SPEC-042", "--json", "--steps", _steps_file(in_repo, _MATCHING_STEPS)]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["spec"] == "SPEC-042"
    assert payload["verdict"] == "green"
    assert payload["totals"]["passed"] == 1
    assert payload["scenarios"][0]["status"] == "passed"


def test_ci_mode_marks_first_run_then_not(in_repo):
    steps = _steps_file(in_repo, _MATCHING_STEPS)

    first = runner.invoke(app, ["verify", "SPEC-042", "--ci", "--steps", steps])
    assert first.exit_code == 0, first.output
    assert json.loads(first.output)["first_run"] is True

    second = runner.invoke(app, ["verify", "SPEC-042", "--ci", "--steps", steps])
    assert json.loads(second.output)["first_run"] is False


def test_local_run_does_not_persist_first_run(in_repo):
    steps = _steps_file(in_repo, _MATCHING_STEPS)
    # roda local (sem --ci) primeiro, depois no CI: o first-run deve ser do CI
    runner.invoke(app, ["verify", "SPEC-042", "--steps", steps])

    ci_run = runner.invoke(app, ["verify", "SPEC-042", "--ci", "--json", "--steps", steps])

    assert json.loads(ci_run.output)["first_run"] is True


def test_a_missing_spec_is_reported(in_repo):
    result = runner.invoke(app, ["verify", "SPEC-999"])

    assert result.exit_code == 1
    assert "não encontrada" in result.output


def test_verify_is_discoverable(in_repo):
    result = runner.invoke(app, ["--help"])

    assert "verify" in result.output
