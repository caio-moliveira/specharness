"""`specharness connect tracker` — the Redmine screen (SPEC-007).

Hermetic: the Redmine client is monkeypatched and the database is a real SQLite
in a tmp dir. The load-bearing assertions are idempotency (métrica 2/3), the API
key never reaching the output (métrica 3 análoga) and the guidance when config or
key is missing.
"""

from __future__ import annotations

import pytest
from specharness_cli.main import app
from specharness_core.ports.tracker import WorkItem
from typer.testing import CliRunner

runner = CliRunner()
SECRET = "redmine-secret-key"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("REDMINE_API_KEY", raising=False)
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_config(tmp_path):
    (tmp_path / "specharness.yaml").write_text(
        "tracker:\n  url: https://redmine.ex\n  project: proj\n", encoding="utf-8"
    )


class FakeRedmineClient:
    items = [
        WorkItem(origin="redmine", external_id="1", kind="issue", title="I1", state="New"),
        WorkItem(origin="redmine", external_id="9", kind="version", title="Sprint 1", state="open"),
    ]

    def __init__(self, base_url, api_key, project, **kwargs):
        self._key = api_key

    def work_items(self):
        yield from self.items

    @property
    def origin(self):
        return "redmine"


@pytest.fixture
def fake_redmine(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.RedmineClient", FakeRedmineClient)


def test_connect_tracker_imports_workitems(monkeypatch, clean_env, fake_redmine):
    _write_config(clean_env)
    monkeypatch.setenv("REDMINE_API_KEY", SECRET)

    result = runner.invoke(app, ["connect", "tracker"])

    assert result.exit_code == 0, result.output
    assert "Redmine" in result.output
    assert "2 WorkItems" in result.output
    assert "2 novos" in result.output


def test_second_run_is_idempotent(monkeypatch, clean_env, fake_redmine):
    _write_config(clean_env)
    monkeypatch.setenv("REDMINE_API_KEY", SECRET)
    first = runner.invoke(app, ["connect", "tracker"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["connect", "tracker"])

    assert second.exit_code == 0, second.output
    assert "nada novo" in second.output.lower()


def test_missing_config_blocks_with_guidance(monkeypatch, clean_env, fake_redmine):
    monkeypatch.setenv("REDMINE_API_KEY", SECRET)

    result = runner.invoke(app, ["connect", "tracker"])

    assert result.exit_code == 1
    assert "tracker.url" in result.output


def test_missing_api_key_blocks_with_guidance(clean_env, fake_redmine):
    _write_config(clean_env)

    result = runner.invoke(app, ["connect", "tracker"])

    assert result.exit_code == 1
    assert "REDMINE_API_KEY" in result.output


def test_the_api_key_never_appears_in_the_output(monkeypatch, clean_env, fake_redmine):
    _write_config(clean_env)
    monkeypatch.setenv("REDMINE_API_KEY", SECRET)

    result = runner.invoke(app, ["connect", "tracker"])

    assert SECRET not in result.output


def test_connect_tracker_is_discoverable(fake_redmine):
    result = runner.invoke(app, ["connect", "--help"])

    assert "tracker" in result.output
