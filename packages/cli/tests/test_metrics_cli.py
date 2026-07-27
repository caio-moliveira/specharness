"""`specharness metrics <sprint>` — snapshot de métricas objetivas (SPEC-013)."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest
from specharness_adapters.db import ScenarioRunStore, SqlAlchemyDatabaseGateway
from specharness_cli.main import app
from specharness_core import ScenarioRun
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from typer.testing import CliRunner

runner = CliRunner()


def _spec(status: str, sprint: str = "2026-Z1") -> str:
    return (
        "---\n"
        "spec: SPEC-050\n"
        'title: "M"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        f"sprint: {sprint}\n"
        'success_metrics: ["m < 1s"]\n'
        'acceptance: ["a"]\n'
        "---\n\n## Contexto\n"
    )


def _git(repo: Path, *args: str, when: datetime | None = None) -> str:
    env = None
    if when is not None:
        import os

        stamp = when.isoformat()
        env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=env
    ).stdout


@pytest.fixture
def repo(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.chdir(tmp_path)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True, capture_output=True)
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "Tester")

    specs = tmp_path / "specs"
    specs.mkdir()
    spec_path = specs / "SPEC-050-x.md"

    # status history: ready (day 1) -> done (day 4) => cycle time 3 days
    spec_path.write_text(_spec("ready"))
    _git(tmp_path, "add", "specs/SPEC-050-x.md")
    _git(tmp_path, "commit", "-q", "-m", "chore: ready", when=datetime(2026, 7, 1))
    spec_path.write_text(_spec("done"))
    _git(tmp_path, "add", "specs/SPEC-050-x.md")
    _git(tmp_path, "commit", "-q", "-m", "chore: done", when=datetime(2026, 7, 4))

    # a code commit carrying the spec's trailer (counts as a commit; adds lines)
    (tmp_path / "data.txt").write_text("a\nb\nc\n")
    _git(tmp_path, "add", "data.txt")
    _git(tmp_path, "commit", "-q", "-m", "feat: x\n\nSpec: SPEC-050", when=datetime(2026, 7, 2))

    # seed scenario_runs in the SAME sqlite the CLI will open (cwd project root)
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()
    ScenarioRunStore(target).record(
        [
            ScenarioRun("SPEC-050", "c1", "passed", first_run=True),
            ScenarioRun("SPEC-050", "c2", "failed", first_run=True),
        ],
        datetime(2026, 7, 4, 10),
    )
    return tmp_path


def test_a_query_by_author_is_rejected(repo):
    result = runner.invoke(app, ["metrics", "2026-Z1", "--by", "sprint,author"])

    assert result.exit_code == 2
    assert "ADR-008" in result.output
    assert "author" in result.output


def test_snapshot_derives_metrics_from_raw_artifacts(repo):
    result = runner.invoke(app, ["metrics", "2026-Z1", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["sprint"] == "2026-Z1"
    assert payload["series"] == 1
    spec = payload["specs"][0]
    assert spec["spec"] == "SPEC-050"
    # cycle time = 3 days between the ready and done commits, straight from git
    assert spec["cycle_time_seconds"] == 3 * 24 * 3600
    # first-run pass rate = 1 of 2 first-run scenarios passed (from scenario_runs,
    # never from any self-reported number)
    assert spec["first_run_pass_rate"] == 0.5
    assert spec["commits"] == 1


def test_recording_twice_appends_a_new_series(repo):
    first = runner.invoke(app, ["metrics", "2026-Z1", "--json"])
    second = runner.invoke(app, ["metrics", "2026-Z1", "--json"])

    assert json.loads(first.output)["series"] == 1
    assert json.loads(second.output)["series"] == 2


def test_an_empty_sprint_is_reported(repo):
    result = runner.invoke(app, ["metrics", "2026-NOPE"])

    assert result.exit_code == 1
    assert "nenhuma spec" in result.output


def test_hygiene_is_collected_from_a_base_ref(repo):
    # add a tampering commit (removes an assert in a test file) with the trailer
    test_file = repo / "packages" / "core" / "tests" / "test_x.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("def test_x():\n    assert foo() == 1\n    bar()\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "test: seed\n\nSpec: SPEC-050")
    base = _git(repo, "rev-parse", "HEAD").strip()
    test_file.write_text("def test_x():\n    bar()\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "test: drop assert\n\nSpec: SPEC-050")

    result = runner.invoke(app, ["metrics", "2026-Z1", "--json", "--base", base])

    assert result.exit_code == 0, result.output
    hygiene = json.loads(result.output)["hygiene"]
    assert any(h["kind"] == "assert-removed" and h["spec"] == "SPEC-050" for h in hygiene)


def test_metrics_is_discoverable(repo):
    result = runner.invoke(app, ["--help"])
    assert "metrics" in result.output
