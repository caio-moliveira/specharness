"""`specharness ready <spec>` — deterministic Readiness Gate (SPEC-010)."""

from __future__ import annotations

import pytest
from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _good_spec(spec_id: str, deps: str = "[SPEC-003]", status: str = "approved") -> str:
    return (
        "---\n"
        f"spec: {spec_id}\n"
        f'title: "T {spec_id}"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        "sprint: 2026-A2\n"
        "tracker_refs: []\n"
        f"depends_on: {deps}\n"
        "adrs: []\n"
        "success_metrics:\n"
        '  - "linking em < 500ms"\n'
        "acceptance:\n"
        '  - "Commit com trailer válido é vinculado à spec"\n'
        "---\n\n"
        "## Cenários\n\n"
        "```gherkin\n"
        "# language: pt\n"
        "Funcionalidade: linking\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        "    Então o commit é vinculado à spec\n"
        "```\n"
    )


@pytest.fixture(autouse=True)
def in_repo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    return tmp_path


def _write(tmp_path, spec_id, text):
    (tmp_path / "specs" / f"{spec_id}-x.md").write_text(text, encoding="utf-8")


def test_ready_passes_a_complete_spec(in_repo):
    _write(in_repo, "SPEC-003", _good_spec("SPEC-003", deps="[]"))
    _write(in_repo, "SPEC-042", _good_spec("SPEC-042"))

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 0, result.output
    assert "passa no piso" in result.output


def test_ready_blocks_and_points_at_an_uncovered_criterion(in_repo):
    text = _good_spec("SPEC-042").replace(
        '  - "Commit com trailer válido é vinculado à spec"\n',
        '  - "Commit com trailer válido é vinculado à spec"\n'
        '  - "O relatório é exportado em PDF assinado"\n',
    )
    _write(in_repo, "SPEC-003", _good_spec("SPEC-003", deps="[]"))
    _write(in_repo, "SPEC-042", text)

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "sem cenário que o cubra" in result.output
    assert "acceptance[2]" in result.output


def test_ready_blocks_an_archived_dependency(in_repo):
    _write(in_repo, "SPEC-003", _good_spec("SPEC-003", deps="[]", status="archived"))
    _write(in_repo, "SPEC-042", _good_spec("SPEC-042"))

    result = runner.invoke(app, ["ready", "SPEC-042"])

    assert result.exit_code == 1
    assert "archived" in result.output


def test_ready_reports_a_missing_spec(in_repo):
    result = runner.invoke(app, ["ready", "SPEC-999"])

    assert result.exit_code == 1
    assert "não encontrada" in result.output


def test_ready_is_discoverable_from_help(in_repo):
    result = runner.invoke(app, ["--help"])

    assert "ready" in result.output
