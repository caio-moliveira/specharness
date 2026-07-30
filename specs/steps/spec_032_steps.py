"""Step definitions da SPEC-032 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-032 --steps specs/steps/spec_032_steps.py`.
Higiene: `link_commits` puro do core. Hook: o `trailer_check.py` real, rodando
como subprocesso (o mesmo caminho do pre-commit) sobre mensagem temporária.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_core import link_commits
from specharness_core.ports.repository import Commit

registry = StepRegistry()

_state: dict[str, Any] = {}

_HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "trailer_check.py"


def _commit(sha: str, message: str) -> Commit:
    return Commit(
        sha=sha,
        author="Ana",
        authored_at=datetime(2026, 7, 30),
        message=message,
        spec_trailers=(),
    )


@registry.step(r"um commit de merge sem trailer de spec")
def _given_merge_commit() -> None:
    _state.clear()
    _state["commits"] = [_commit("m" * 40, "Merge pull request #7 from x/y")]


@registry.step(r"um commit fixup! sem trailer de spec")
def _given_fixup_commit() -> None:
    _state.clear()
    _state["commits"] = [_commit("f" * 40, "fixup! feat: x")]


@registry.step(r"um commit comum sem trailer de spec")
def _given_plain_commit() -> None:
    _state.clear()
    _state["commits"] = [_commit("p" * 40, "feat: sem trailer")]


@registry.step(r"o track processa os commits")
def _when_linking_runs() -> None:
    _state["result"] = link_commits(_state["commits"], [])


@registry.step(r"o commit de merge não entra na contagem de commits órfãos")
def _then_merge_not_orphan() -> None:
    assert _state["result"].orphan_commits == (), _state["result"].orphan_commits


@registry.step(r"o commit fixup não entra na contagem de commits órfãos")
def _then_fixup_not_orphan() -> None:
    assert _state["result"].orphan_commits == (), _state["result"].orphan_commits


@registry.step(r"o commit entra na contagem de commits órfãos")
def _then_plain_is_orphan() -> None:
    assert _state["result"].orphan_commits == ("p" * 40,), _state["result"].orphan_commits


@registry.step(r"uma mensagem de commit com Spec: separado dos demais trailers por linha em branco")
def _given_split_trailer_message() -> None:
    _state.clear()
    _state["message"] = "feat: x\n\nSpec: SPEC-003\n\nCo-Authored-By: Fulana <f@exemplo.com>\n"


@registry.step(r"o hook de commit-msg valida a mensagem")
def _when_hook_runs() -> None:
    msg_file = Path(tempfile.mkdtemp(prefix="spec032-")) / "COMMIT_EDITMSG"
    msg_file.write_text(_state["message"], encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(_HOOK), str(msg_file)], capture_output=True, text=True
    )
    _state["output"] = proc.stdout + proc.stderr
    _state["exit_code"] = proc.returncode


@registry.step(
    r"a rejeição explica que todos os trailers devem ficar no mesmo bloco final "
    r"e mostra um exemplo com Spec: e Co-Authored-By juntos"
)
def _then_rejection_teaches_the_block() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    assert "ÚLTIMO bloco" in _state["output"], _state["output"]
    assert "Co-Authored-By" in _state["output"], _state["output"]
    assert "Spec: SPEC-003" in _state["output"], _state["output"]
