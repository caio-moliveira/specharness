"""A transição gravada pelo ready alimenta o cycle time (SPEC-033, cenário 5).

Integração com git real: um repo temporário onde o `ready --override` grava
status: ready, o commit registra a transição, o done entra num commit seguinte
e o StatusHistoryReader + cycle_time_seconds fecham a conta.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from specharness_adapters.metrics import StatusHistoryReader
from specharness_cli.main import app
from specharness_core import cycle_time_seconds
from typer.testing import CliRunner

runner = CliRunner()

_SPEC = (
    "---\n"
    "spec: SPEC-042\n"
    'title: "T"\n'
    "status: approved\n"
    "type: feature\n"
    'success_metrics: ["m < 1s"]\n'
    'acceptance: ["Commit com trailer válido é vinculado à spec"]\n'
    "---\n\n"
    "```gherkin\n"
    "# language: pt\n"
    "Funcionalidade: linking\n\n"
    "  Cenário: trailer válido vincula\n"
    "    Dado um commit com trailer\n"
    "    Quando o track roda\n"
    "    Então o commit é vinculado à spec\n"
    "```\n"
)


def _git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=path,
        check=True,
        capture_output=True,
    )


def test_promoted_transition_feeds_cycle_time(tmp_path, monkeypatch):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    relpath = "specs/SPEC-042-t.md"
    (tmp_path / "specs").mkdir()
    spec_path = tmp_path / relpath
    spec_path.write_text(_SPEC, "utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "spec approved")

    result = runner.invoke(
        app, ["ready", "SPEC-042", "--override", "--author", "tl", "--reason", "r"]
    )
    assert result.exit_code == 0, result.output
    assert "status: ready" in spec_path.read_text("utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "spec ready")

    spec_path.write_text(spec_path.read_text("utf-8").replace("status: ready", "status: done"))
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "spec done")

    transitions = StatusHistoryReader(tmp_path, relpath).transitions("SPEC-042")
    statuses = [t.to_status.value for t in transitions]
    assert "ready" in statuses and "done" in statuses, statuses
    assert cycle_time_seconds(transitions) is not None
