"""`specharness connect jira` — a tela do Jira (SPEC-019).

Hermetic: the Jira client is monkeypatched and the database is a real SQLite in
a tmp dir. The load-bearing assertions are idempotency, the atomicity of a
failed import (cenário "falha de rede": nada persiste), the guidance when
config or credential is missing, and the token never reaching the output.
"""

from __future__ import annotations

import pytest
from specharness_cli.main import app
from specharness_core.ports.tracker import TrackerError, WorkItem
from typer.testing import CliRunner

runner = CliRunner()
SECRET = "jira-secret-token"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for var in ("JIRA_URL", "JIRA_EMAIL", "JIRA_TOKEN", "SPECHARNESS_DATABASE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write_config(tmp_path):
    (tmp_path / "specharness.yaml").write_text("jira:\n  project: KAN\n", encoding="utf-8")


def _set_credentials(monkeypatch):
    monkeypatch.setenv("JIRA_URL", "https://jira.ex")
    monkeypatch.setenv("JIRA_EMAIL", "eu@ex.com")
    monkeypatch.setenv("JIRA_TOKEN", SECRET)


class FakeJiraClient:
    items = [
        WorkItem(origin="jira", external_id="KAN-1", kind="story", title="S1", state="To Do"),
        WorkItem(origin="jira", external_id="KAN-2", kind="task", title="T1", state="Done"),
    ]

    def __init__(self, base_url, email, token, project, **kwargs):
        self._token = token

    def work_items(self):
        yield from self.items

    @property
    def origin(self):
        return "jira"


class BrokenMidImportClient(FakeJiraClient):
    """Yields one item, then the network dies (cenário 6)."""

    def work_items(self):
        yield self.items[0]
        raise TrackerError.for_tracker(
            "https://jira.ex", "falha de rede (ConnectError). Verifique a rede e tente de novo"
        )


@pytest.fixture
def fake_jira(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.JiraClient", FakeJiraClient)


def test_connect_jira_imports_workitems(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    _set_credentials(monkeypatch)

    result = runner.invoke(app, ["connect", "jira"])

    assert result.exit_code == 0, result.output
    assert "Jira" in result.output
    assert "2 WorkItems" in result.output
    assert "2 novos" in result.output


def test_second_run_is_idempotent(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    _set_credentials(monkeypatch)
    first = runner.invoke(app, ["connect", "jira"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["connect", "jira"])

    assert second.exit_code == 0, second.output
    assert "nada novo" in second.output.lower()


def test_a_mid_import_network_failure_persists_nothing(monkeypatch, clean_env):
    """Cenário 6: o import interrompido não deixa WorkItem parcial no banco."""
    _write_config(clean_env)
    _set_credentials(monkeypatch)
    monkeypatch.setattr("specharness_cli.main.JiraClient", BrokenMidImportClient)

    broken = runner.invoke(app, ["connect", "jira"])
    assert broken.exit_code == 1
    assert "rede" in broken.output.lower()
    assert "tente de novo" in broken.output.lower()

    monkeypatch.setattr("specharness_cli.main.JiraClient", FakeJiraClient)
    recovered = runner.invoke(app, ["connect", "jira"])

    assert recovered.exit_code == 0, recovered.output
    assert "2 novos" in recovered.output  # nada tinha sido persistido antes


def test_missing_config_blocks_with_guidance(monkeypatch, clean_env, fake_jira):
    _set_credentials(monkeypatch)

    result = runner.invoke(app, ["connect", "jira"])

    assert result.exit_code == 1
    assert "jira.project" in result.output


def test_missing_url_blocks_with_guidance(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    monkeypatch.setenv("JIRA_EMAIL", "eu@ex.com")
    monkeypatch.setenv("JIRA_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "jira"])

    assert result.exit_code == 1
    assert "JIRA_URL" in result.output


def test_missing_email_blocks_with_guidance(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    monkeypatch.setenv("JIRA_URL", "https://jira.ex")
    monkeypatch.setenv("JIRA_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "jira"])

    assert result.exit_code == 1
    assert "JIRA_EMAIL" in result.output


def test_missing_token_blocks_naming_the_env_var(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    monkeypatch.setenv("JIRA_URL", "https://jira.ex")
    monkeypatch.setenv("JIRA_EMAIL", "eu@ex.com")

    result = runner.invoke(app, ["connect", "jira"])

    assert result.exit_code == 1
    assert "JIRA_TOKEN" in result.output


def test_the_token_never_appears_in_the_output(monkeypatch, clean_env, fake_jira):
    _write_config(clean_env)
    _set_credentials(monkeypatch)

    result = runner.invoke(app, ["connect", "jira"])

    assert SECRET not in result.output


def test_connect_jira_is_discoverable(fake_jira):
    result = runner.invoke(app, ["connect", "--help"])

    assert "jira" in result.output
