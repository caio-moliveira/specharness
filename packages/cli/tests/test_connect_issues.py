"""`specharness connect issues` — GitHub Issues import (SPEC-008).

Hermetic: the git reader and the issues client are monkeypatched, the database
is a real SQLite in a tmp dir. Load-bearing: idempotency, the token never in the
output, and the GITHUB_TOKEN guidance when it is missing.
"""

from __future__ import annotations

import pytest
from specharness_cli.main import app
from specharness_core.ports.repository import RepoRef, RepositoryError
from specharness_core.ports.tracker import WorkItem
from typer.testing import CliRunner

runner = CliRunner()
SECRET = "ghp_super_secret_token"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


class FakeReader:
    def __init__(self, path, run=None):
        pass

    def remote_ref(self, remote="origin"):
        return RepoRef("acme", "tool")


class FakeIssuesClient:
    items = [
        WorkItem(origin="github", external_id="1", kind="issue", title="Bug", state="open"),
        WorkItem(origin="github", external_id="2", kind="issue", title="Feat", state="closed"),
    ]

    def __init__(self, ref, token, **kwargs):
        self._token = token

    def work_items(self):
        yield from self.items


@pytest.fixture
def fake_sources(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.LocalGitCommitReader", FakeReader)
    monkeypatch.setattr("specharness_cli.main.GitHubIssuesClient", FakeIssuesClient)


def test_connect_issues_imports_workitems(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "issues"])

    assert result.exit_code == 0, result.output
    assert "acme/tool" in result.output
    assert "2 WorkItems" in result.output
    assert "2 novos" in result.output


def test_second_run_is_idempotent(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)
    first = runner.invoke(app, ["connect", "issues"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["connect", "issues"])

    assert second.exit_code == 0, second.output
    assert "nada novo" in second.output.lower()


def test_missing_token_blocks_naming_github_token(fake_sources):
    result = runner.invoke(app, ["connect", "issues"])

    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.output


def test_the_token_never_appears_in_the_output(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "issues"])

    assert SECRET not in result.output


def test_a_non_github_remote_exits_nonzero(monkeypatch):
    class BadReader:
        def __init__(self, path, run=None):
            pass

        def remote_ref(self, remote="origin"):
            raise RepositoryError.for_repo("?", "sem remote do GitHub")

    monkeypatch.setattr("specharness_cli.main.LocalGitCommitReader", BadReader)

    result = runner.invoke(app, ["connect", "issues"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_connect_issues_is_discoverable(fake_sources):
    result = runner.invoke(app, ["connect", "--help"])

    assert "issues" in result.output
