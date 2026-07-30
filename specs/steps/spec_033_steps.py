"""Step definitions da SPEC-033 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-033 --steps specs/steps/spec_033_steps.py`.
Roda o `ready` real via CliRunner em tmp dirs (LLM substituída no módulo da
CLI, padrão de tests/test_ready.py); o cenário do cycle time usa git real e o
StatusHistoryReader de produção.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from specharness_adapters.metrics import StatusHistoryReader
from specharness_adapters.verify import StepRegistry
from specharness_cli import main
from specharness_core import Evaluation, cycle_time_seconds
from specharness_core.ports.database import DATABASE_URL_ENV
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {}


def _spec_doc(status: str, *, floor_passes: bool = True) -> str:
    acceptance = (
        'acceptance: ["Commit com trailer válido é vinculado à spec"]\n'
        if floor_passes
        else "acceptance: []\n"
    )
    return (
        "---\n"
        "spec: SPEC-042\n"
        'title: "T"\n'
        f"status: {status}\n"
        "type: feature\n"
        "updated: 2026-07-01\n"
        'success_metrics: ["linking em < 500ms"]\n' + acceptance + "---\n\n"
        "```gherkin\n"
        "# language: pt\n"
        "Funcionalidade: linking\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        "    Então o commit é vinculado à spec\n"
        "```\n"
    )


def _prepare(status: str, *, floor_passes: bool = True, override: bool = False) -> None:
    _state.clear()
    _state["doc"] = _spec_doc(status, floor_passes=floor_passes)
    _state["args"] = (
        ["ready", "SPEC-042", "--override", "--author", "tl", "--reason", "prazo"]
        if override
        else ["ready", "SPEC-042"]
    )


def _run_ready() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="spec033-"))
    (tmp / "specs").mkdir()
    spec_path = tmp / "specs" / "SPEC-042-t.md"
    spec_path.write_text(_state["doc"], "utf-8")
    _state["spec_path"] = spec_path
    _state["before"] = _state["doc"]
    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    originals = (main.detect_providers, main.evaluate_spec)
    main.detect_providers = lambda env: ["anthropic"]
    main.evaluate_spec = lambda text, client: Evaluation(
        score=95, issues=(), model="fake/model", cost_usd=0.0, cached=False
    )
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(main.app, _state["args"])
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        os.chdir(saved_cwd)
        main.detect_providers, main.evaluate_spec = originals
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


@registry.step(r"uma spec em status approved que passa no piso determinístico e na camada LLM")
def _given_approved_passing() -> None:
    _prepare("approved")


@registry.step(r"uma spec em status approved e um override com autor e justificativa")
def _given_approved_with_override() -> None:
    _prepare("approved", override=True)


@registry.step(r"uma spec em status draft que passa nas duas camadas")
def _given_draft_passing() -> None:
    _prepare("draft")


@registry.step(r"uma spec em status approved que reprova no piso determinístico")
def _given_approved_failing_floor() -> None:
    _prepare("approved", floor_passes=False)


@registry.step(r"o ready roda sobre ela")
def _when_ready_runs() -> None:
    _run_ready()


@registry.step(r"o ready roda com a opção de override")
def _when_ready_runs_with_override() -> None:
    _run_ready()


@registry.step(r"o arquivo da spec passa a ter status ready e a promoção é anunciada na saída")
def _then_promoted_and_announced() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert "status: ready" in _state["spec_path"].read_text("utf-8")
    assert "status: ready gravado" in " ".join(_state["output"].split()), _state["output"]


@registry.step(r"o arquivo da spec passa a ter status ready")
def _then_promoted() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert "status: ready" in _state["spec_path"].read_text("utf-8")


@registry.step(r"o arquivo permanece em draft e a saída orienta a aprovar a spec primeiro")
def _then_draft_untouched_with_guidance() -> None:
    assert "status: draft" in _state["spec_path"].read_text("utf-8")
    assert "aprove" in _state["output"].lower(), _state["output"]


@registry.step(r"o arquivo da spec permanece exatamente como estava")
def _then_file_untouched() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    assert _state["spec_path"].read_text("utf-8") == _state["before"]


def _git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=path,
        check=True,
        capture_output=True,
    )


@registry.step(r"uma spec promovida a ready pelo veredito e depois marcada done pelo CI")
def _given_full_lifecycle_in_git() -> None:
    _prepare("approved", override=True)
    tmp = Path(tempfile.mkdtemp(prefix="spec033-git-"))
    relpath = "specs/SPEC-042-t.md"
    (tmp / "specs").mkdir()
    spec_path = tmp / relpath
    spec_path.write_text(_state["doc"], "utf-8")
    _git(tmp, "init", "-q")
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-q", "-m", "spec approved")

    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(main.app, _state["args"])
        assert result.exit_code == 0, result.output
    finally:
        os.chdir(saved_cwd)
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db

    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-q", "-m", "spec ready")
    spec_path.write_text(spec_path.read_text("utf-8").replace("status: ready", "status: done"))
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-q", "-m", "spec done")
    _state["repo"] = tmp
    _state["relpath"] = relpath


@registry.step(r"as transições da spec são lidas do histórico git")
def _when_transitions_are_read() -> None:
    _state["transitions"] = StatusHistoryReader(_state["repo"], _state["relpath"]).transitions(
        "SPEC-042"
    )


@registry.step(r"o cycle time entre ready e done é computável")
def _then_cycle_time_computable() -> None:
    statuses = [t.to_status.value for t in _state["transitions"]]
    assert "ready" in statuses and "done" in statuses, statuses
    assert cycle_time_seconds(_state["transitions"]) is not None
