"""`specharness connect repo` — the repository screen of the onboarding (SPEC-006).

Hermetic: the git reader and the GitHub client are monkeypatched, and the
database is a real SQLite in a tmp dir (the default path). The load-bearing
assertions are idempotency (métrica 2), the token never reaching the output
(métrica 3) and the scope guidance when the token is missing (critério 4).
"""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_cli.main import app
from specharness_core.ports.repository import Commit, PullRequest, RepoRef, RepositoryError
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

    def commits(self):
        yield Commit(
            sha="a",
            author="Ana",
            authored_at=datetime(2026, 7, 27),
            message="feat: x\n\nSpec: SPEC-006",
            spec_trailers=("SPEC-006",),
        )
        yield Commit(sha="b", author="Bob", authored_at=datetime(2026, 7, 26), message="chore: y")


class FakeGitHubClient:
    def __init__(self, ref, token, **kwargs):
        self._token = token

    def pull_requests(self):
        yield PullRequest(
            number=1,
            title="t",
            state="open",
            head_branch="feat/x",
            base_branch="main",
            commit_shas=("a",),
        )


@pytest.fixture
def fake_sources(monkeypatch):
    monkeypatch.setattr("specharness_cli.main.LocalGitCommitReader", FakeReader)
    monkeypatch.setattr("specharness_cli.main.GitHubClient", FakeGitHubClient)


def test_connect_repo_ingests_commits_and_prs(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "repo"])

    assert result.exit_code == 0, result.output
    assert "acme/tool" in result.output
    assert "2 commits" in result.output
    assert "1 PRs" in result.output


def test_second_run_is_idempotent(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)
    first = runner.invoke(app, ["connect", "repo"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["connect", "repo"])

    assert second.exit_code == 0, second.output
    assert "nada novo" in second.output.lower()


def test_missing_token_blocks_with_scope_guidance(fake_sources):
    result = runner.invoke(app, ["connect", "repo"])

    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.output
    assert "escopo" in result.output.lower()


def test_the_token_never_appears_in_the_output(monkeypatch, fake_sources):
    monkeypatch.setenv("GITHUB_TOKEN", SECRET)

    result = runner.invoke(app, ["connect", "repo"])

    assert SECRET not in result.output


def test_a_non_github_remote_exits_nonzero(monkeypatch):
    class BadReader:
        def __init__(self, path, run=None):
            pass

        def remote_ref(self, remote="origin"):
            raise RepositoryError.for_repo("?", "sem remote do GitHub")

    monkeypatch.setattr("specharness_cli.main.LocalGitCommitReader", BadReader)

    result = runner.invoke(app, ["connect", "repo"])

    assert result.exit_code == 1
    assert "Traceback" not in result.output


def test_connect_repo_is_discoverable(fake_sources):
    result = runner.invoke(app, ["connect", "--help"])

    assert "repo" in result.output
