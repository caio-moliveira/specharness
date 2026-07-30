"""Step definitions da SPEC-012 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-012 --steps specs/steps/spec_012_steps.py`.
Meta-verificação: os cenários rodam o próprio `verify` (via CliRunner) sobre
specs sintéticas em diretórios temporários, com SQLite próprio por cenário.
O hook de schema (cenário do done fora do CI) roda como subprocesso real.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from specharness_adapters.db import SqlAlchemyDatabaseGateway
from specharness_adapters.verify import StepRegistry
from specharness_cli.main import app
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {}

_REPO_ROOT = Path(__file__).resolve().parents[2]

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
Funcionalidade: exemplo

  Cenário: comportamento observável
    Dado um estado inicial
    Quando a ação acontece
    Então o efeito é observado
```
"""

_PASSING_STEPS = (
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


def _fresh_env(steps_body: str | None) -> None:
    """Um repositório sintético isolado: specs/, steps e SQLite próprios."""
    tmp = Path(tempfile.mkdtemp(prefix="spec012-"))
    (tmp / "specs").mkdir()
    (tmp / "specs" / "SPEC-042-t.md").write_text(_SPEC, "utf-8")
    steps_path = None
    if steps_body is not None:
        steps_path = tmp / "steps.py"
        steps_path.write_text(steps_body, "utf-8")
    _state.clear()
    _state["tmp"] = tmp
    _state["steps"] = str(steps_path) if steps_path else None


def _invoke_verify(*, ci: bool) -> None:
    """Roda o verify no ambiente sintético, controlando o env CI explicitamente."""
    saved_cwd = os.getcwd()
    saved_ci = os.environ.pop("CI", None)
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    if ci:
        os.environ["CI"] = "true"
    args = ["verify", "SPEC-042"]
    if ci:
        args.append("--ci")  # a flag emite o resumo JSON; o env CI cobre o is_ci
    if _state["steps"]:
        args += ["--steps", _state["steps"]]
    try:
        os.chdir(_state["tmp"])
        result = CliRunner().invoke(app, args)
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        os.chdir(saved_cwd)
        os.environ.pop("CI", None)
        if saved_ci is not None:
            os.environ["CI"] = saved_ci
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


def _ci_json() -> dict[str, Any]:
    line = next(line for line in _state["output"].splitlines() if line.startswith("{"))
    return json.loads(line)


@registry.step(r"uma spec em verifying cujos cenários passam na suite do repositório")
def _given_green_scenarios() -> None:
    _fresh_env(_PASSING_STEPS)


@registry.step(r"uma spec em verifying com um cenário falhando")
def _given_failing_scenario() -> None:
    _fresh_env(_FAILING_STEPS)


@registry.step(r"uma spec que acabou de sair de ready para in_progress")
def _given_fresh_implementation() -> None:
    _fresh_env(_PASSING_STEPS)


@registry.step(r"uma spec em verifying com o status editado localmente para done")
def _given_local_done_edit() -> None:
    _fresh_env(None)
    path = _state["tmp"] / "specs" / "SPEC-042-t.md"
    path.write_text(_SPEC.replace("status: verifying", "status: done"), "utf-8")
    _state["done_path"] = path


@registry.step(r"uma spec cujos cenários foram executados localmente antes de qualquer run no CI")
def _given_local_run_happened_first() -> None:
    _fresh_env(_PASSING_STEPS)
    _invoke_verify(ci=False)  # execução local, informativa — não conta como first-run
    assert _state["exit_code"] == 0, _state["output"]


@registry.step(r"uma spec com cenário sem step definition correspondente")
def _given_no_steps() -> None:
    _fresh_env(None)


@registry.step(r"uma execução do verify em modo CI")
def _given_ci_execution() -> None:
    _fresh_env(_PASSING_STEPS)


@registry.step(r"o verify executa no CI")
def _when_verify_runs_in_ci() -> None:
    _invoke_verify(ci=True)


@registry.step(r"o verify executa pela primeira vez após a implementação")
def _when_first_verify_after_implementation() -> None:
    _invoke_verify(ci=True)


@registry.step(r"a validação de schema processa a mudança fora do CI")
def _when_schema_hook_runs_locally() -> None:
    env = {k: v for k, v in os.environ.items() if k != "CI"}
    proc = subprocess.run(
        [
            sys.executable,
            str(_REPO_ROOT / ".claude" / "hooks" / "schema_validate.py"),
            str(_state["done_path"]),
        ],
        capture_output=True,
        text=True,
        env=env,
        cwd=_REPO_ROOT,
    )
    _state["output"] = proc.stdout + proc.stderr
    _state["exit_code"] = proc.returncode


@registry.step(r"o primeiro run no CI acontece após ready")
def _when_first_ci_run() -> None:
    _invoke_verify(ci=True)


@registry.step(r"o verify executa")
def _when_verify_runs_locally() -> None:
    _invoke_verify(ci=False)


@registry.step(r"o verify termina")
def _when_verify_finishes() -> None:
    _invoke_verify(ci=True)


@registry.step(r"a transição para done é liberada e o ScenarioRun registra o resultado")
def _then_done_allowed_and_persisted() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    payload = _ci_json()
    assert payload["verdict"] == "green", payload
    # persistência: o run ficou registrado no banco do repositório sintético
    from specharness_adapters.db import ScenarioRunStore

    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=_state["tmp"])
    SqlAlchemyDatabaseGateway(target).migrate()
    assert ScenarioRunStore(target).has_first_run("SPEC-042")


@registry.step(r"a transição para done é bloqueada e a falha aponta o cenário")
def _then_done_blocked_with_scenario() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    payload = _ci_json()
    assert payload["verdict"] != "green", payload
    failed = [s["title"] for s in payload["scenarios"] if s["status"] == "failed"]
    assert "comportamento observável" in failed, payload


@registry.step(r"o resultado é registrado com a marcação de first-run")
def _then_marked_first_run() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _ci_json()["first_run"] is True


@registry.step(r"a transição é rejeitada com referência ao ADR-016")
def _then_rejected_with_adr() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    assert "ADR-016" in _state["output"], _state["output"]


@registry.step(r"apenas o run do CI é registrado com a marcação de first-run")
def _then_only_ci_run_is_first() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _ci_json()["first_run"] is True  # o run local anterior não consumiu o first-run


@registry.step(r"o cenário é reportado como pendente com orientação de implementação")
def _then_pending_with_guidance() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    flat = " ".join(_state["output"].split())  # o console quebra linhas na largura
    assert "pendente" in flat.lower()
    assert "implemente o passo" in flat, flat


@registry.step(r"a saída é um resumo JSON legível por máquina e o exit code reflete o veredito")
def _then_machine_readable_summary() -> None:
    payload = _ci_json()
    assert payload["verdict"] == "green"
    assert payload["totals"]["passed"] == 1
    assert _state["exit_code"] == 0
