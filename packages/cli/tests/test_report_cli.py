"""`specharness report <sprint>` — relatório tabular + narrativa (SPEC-015)."""

from __future__ import annotations

import zipfile
from datetime import datetime

import pytest
from specharness_adapters.db import (
    MetricSnapshotStore,
    PerceptionStore,
    RepositoryStore,
    SqlAlchemyDatabaseGateway,
)
from specharness_cli.main import app
from specharness_core import PerceptionSample, SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.repository import Commit
from typer.testing import CliRunner

runner = CliRunner()


def _spec(status: str = "done", sprint: str = "2026-A4") -> str:
    return (
        "---\n"
        "spec: SPEC-013\n"
        'title: "R"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        f"sprint: {sprint}\n"
        'success_metrics: ["m < 1s"]\n'
        'acceptance: ["a"]\n'
        "---\n\n## Contexto\n"
    )


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    for var in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs" / "SPEC-013-x.md").write_text(_spec(), "utf-8")

    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()
    MetricSnapshotStore(target).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-013", 360000.0, 0.9, 2, 0.1, 0.2, 1.0, 1.5, commits=8),),
        ),
        datetime(2026, 7, 27),
    )
    PerceptionStore(target).record_sample(
        PerceptionSample(
            "acme#1", "SPEC-013", "2026-A4", "Claude Code", "opus", 5, "leve", "economizou"
        ),
        datetime(2026, 7, 27),
    )
    RepositoryStore(target).sync(
        "acme/tool", [Commit("a", "Ana", datetime(2026, 7, 27), "m", ("SPEC-013",))], []
    )
    return tmp_path


def test_tabular_report_without_llm(env):
    # no LLM configured -> the full tabular report is still produced (acceptance[4])
    result = runner.invoke(app, ["report", "2026-A4"])

    assert result.exit_code == 0, result.output
    assert "# Relatório da sprint 2026-A4" in result.output
    assert "Specs planejadas: 1" in result.output
    assert "Specs concluídas: 1" in result.output
    assert "| SPEC-013 |" in result.output
    assert "## Percepção" in result.output


def test_narrative_flag_without_llm_still_gives_the_table(env):
    result = runner.invoke(app, ["report", "2026-A4", "--narrative"])
    assert result.exit_code == 0, result.output
    assert "# Relatório da sprint 2026-A4" in result.output
    assert "sem LLM" in result.output  # narrative skipped, table intact


def test_writes_markdown_and_docx_files(env):
    md_path = env / "out.md"
    docx_path = env / "out.docx"
    result = runner.invoke(
        app, ["report", "2026-A4", "--out", str(md_path), "--docx", str(docx_path)]
    )
    assert result.exit_code == 0, result.output
    assert "Relatório da sprint" in md_path.read_text(encoding="utf-8")
    with zipfile.ZipFile(docx_path) as zf:
        document = zf.read("word/document.xml").decode("utf-8")
    assert "SPEC-013" in document


def test_report_is_discoverable(env):
    assert "report" in runner.invoke(app, ["--help"]).output
