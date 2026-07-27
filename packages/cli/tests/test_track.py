"""`specharness track` — commit<->spec linking view (SPEC-009).

Hermetic: the commit reader is monkeypatched and the spec registry either comes
from a monkeypatched loader (logic tests) or from real files on disk (loader
test). The database is a real SQLite in a tmp dir.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_cli.main import app
from specharness_core import SpecInfo
from specharness_core.ports.repository import Commit
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    return tmp_path


def _commit(sha, trailers=()):
    return Commit(
        sha=sha,
        author="Ana",
        authored_at=datetime(2026, 7, 27),
        message="m",
        spec_trailers=trailers,
    )


def _fake_store(monkeypatch, commits):
    class FakeStore:
        def __init__(self, target):
            pass

        def all_commits(self):
            return commits

    monkeypatch.setattr("specharness_cli.main.RepositoryStore", FakeStore)


def _fake_specs(monkeypatch, specs):
    monkeypatch.setattr("specharness_cli.main._load_spec_infos", lambda: specs)


def test_track_shows_links_and_the_hygiene_report(monkeypatch):
    _fake_store(
        monkeypatch,
        [
            _commit("aaaaaaaaaa1", ("SPEC-042",)),  # vínculo válido
            _commit("bbbbbbbbbb2", ()),  # commit órfão
            _commit("cccccccccc3", ("SPEC-999",)),  # vínculo inválido
        ],
    )
    _fake_specs(
        monkeypatch,
        [
            SpecInfo("SPEC-042", "in_progress", "2026-A2"),
            SpecInfo("SPEC-050", "in_progress", "2026-A2"),  # spec órfã
        ],
    )

    result = runner.invoke(app, ["track"])

    assert result.exit_code == 0, result.output
    assert "SPEC-042" in result.output  # vínculo válido na pipeline
    assert "1 vínculos válidos" in result.output
    assert "1 inválidos" in result.output
    assert "SPEC-999" in result.output  # sinalizado, não ignorado
    assert "1 commits órfãos" in result.output
    assert "SPEC-050" in result.output  # spec órfã listada


def test_track_reports_a_clean_pipeline(monkeypatch):
    _fake_store(monkeypatch, [_commit("a", ("SPEC-042",))])
    _fake_specs(monkeypatch, [SpecInfo("SPEC-042", "in_progress", "2026-A2")])

    result = runner.invoke(app, ["track"])

    assert result.exit_code == 0, result.output
    assert "limpa" in result.output.lower()


def test_track_is_discoverable_from_help():
    result = runner.invoke(app, ["--help"])

    assert "track" in result.output


# --- listagem de órfãos (SPEC-017) ------------------------------------------


def test_track_orphans_flag_lists_shas(monkeypatch):
    _fake_store(
        monkeypatch,
        [_commit("aaaaaaaaaa1", ("SPEC-042",)), _commit("bbbbbbbbbb2", ())],
    )
    _fake_specs(monkeypatch, [SpecInfo("SPEC-042", "in_progress", "2026-A2")])

    result = runner.invoke(app, ["track", "--orphans"])

    assert result.exit_code == 0, result.output
    assert "commit órfão" in result.output
    assert "bbbbbbbbbb" in result.output


def test_track_without_the_flag_keeps_the_summary_only(monkeypatch):
    _fake_store(
        monkeypatch,
        [_commit("aaaaaaaaaa1", ("SPEC-042",)), _commit("bbbbbbbbbb2", ())],
    )
    _fake_specs(monkeypatch, [SpecInfo("SPEC-042", "in_progress", "2026-A2")])

    result = runner.invoke(app, ["track"])

    assert "1 commits órfãos" in result.output
    assert "commit órfão (sem trailer" not in result.output


def test_orphans_respects_the_limit(monkeypatch):
    _fake_store(monkeypatch, [_commit(f"orfao{i:06d}xyz", ()) for i in range(5)])
    _fake_specs(monkeypatch, [])

    result = runner.invoke(app, ["track", "--orphans", "--limit", "2"])

    assert result.exit_code == 0, result.output
    assert result.output.count("commit órfão (sem trailer") == 2
    assert "e 3 outro(s)" in result.output


def test_load_spec_infos_reads_the_registry_from_disk(clean_env):
    (clean_env / "specs" / "SPEC-042-x.md").write_text(
        _valid_spec("SPEC-042", "in_progress"), "utf-8"
    )
    (clean_env / "specs" / "SPEC-001-y.md").write_text(_valid_spec("SPEC-001", "done"), "utf-8")
    from specharness_cli.main import _load_spec_infos

    infos = {info.spec_id: info for info in _load_spec_infos()}

    assert infos["SPEC-042"].is_in_progress is True
    assert infos["SPEC-001"].is_in_progress is False


def _valid_spec(spec_id: str, status: str) -> str:
    return (
        "---\n"
        f"spec: {spec_id}\n"
        f'title: "Teste {spec_id}"\n'
        f"status: {status}\n"
        "type: feature\n"
        "owner: caio\n"
        "created: 2026-07-25\n"
        "sprint: 2026-A2\n"
        "tracker_refs: []\n"
        "depends_on: []\n"
        "adrs: []\n"
        "success_metrics:\n"
        '  - "uma métrica"\n'
        "acceptance:\n"
        '  - "um critério"\n'
        "---\n\n## Contexto\n\ntexto\n"
    )
