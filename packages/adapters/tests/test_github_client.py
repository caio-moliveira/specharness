"""The GitHub client (SPEC-006, critérios 3 e 4, métrica 3).

Hermetic: the `fetch` callable is injected, so pagination, mapping and every
error class are proven with no network and no token. The token is never echoed
in an error.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from specharness_adapters.github import GitHubClient
from specharness_core.ports.repository import (
    AuthenticationFailed,
    RateLimited,
    RepoRef,
    RepositoryNotFound,
)

REF = RepoRef("acme", "tool")


def _resp(status, body, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: body, headers=headers or {})


def _pr(number):
    return {
        "number": number,
        "title": f"PR {number}",
        "state": "open",
        "head": {"ref": f"feat/{number}"},
        "base": {"ref": "main"},
    }


class FakeGitHub:
    """Routes fetches by path and page over canned data."""

    def __init__(self, pulls_pages, commits_by_pr):
        self.pulls_pages = pulls_pages
        self.commits_by_pr = commits_by_pr
        self.seen: list[tuple[str, int]] = []

    def fetch(self, path, params):
        page = params["page"]
        self.seen.append((path, page))
        if path.endswith("/pulls"):
            body = self.pulls_pages[page - 1] if page - 1 < len(self.pulls_pages) else []
            return _resp(200, body)
        if path.endswith("/commits"):
            number = int(path.split("/pulls/")[1].split("/")[0])
            body = self.commits_by_pr.get(number, []) if page == 1 else []
            return _resp(200, body)
        return _resp(404, {})


# --- ingestão de PRs com estado, branch e vínculo (critério 3) -------------


def test_ingests_pull_requests_with_state_branch_and_commit_links():
    fake = FakeGitHub(
        pulls_pages=[[_pr(1), _pr(2)]],
        commits_by_pr={1: [{"sha": "aaa"}, {"sha": "bbb"}], 2: [{"sha": "ccc"}]},
    )

    prs = list(GitHubClient(REF, "tok", fetch=fake.fetch).pull_requests())

    assert [p.number for p in prs] == [1, 2]
    assert prs[0].state == "open"
    assert prs[0].head_branch == "feat/1"
    assert prs[0].base_branch == "main"
    assert prs[0].commit_shas == ("aaa", "bbb")
    assert prs[1].commit_shas == ("ccc",)


# --- paginação (métrica 3) -------------------------------------------------


def test_paginates_pulls_until_a_short_page():
    fake = FakeGitHub(pulls_pages=[[_pr(1), _pr(2)], [_pr(3)]], commits_by_pr={})

    prs = list(GitHubClient(REF, "tok", fetch=fake.fetch, per_page=2).pull_requests())

    assert [p.number for p in prs] == [1, 2, 3]
    pull_pages = [page for (path, page) in fake.seen if path.endswith("/pulls")]
    assert pull_pages == [1, 2]  # parou na página curta, não pediu a 3


# --- classificação de erro (critério 4, métrica 3) -------------------------


def test_invalid_auth_raises_authentication_failed():
    with pytest.raises(AuthenticationFailed):
        list(GitHubClient(REF, "bad", fetch=lambda p, q: _resp(401, {})).pull_requests())


def test_rate_limited_403_raises_rate_limited():
    fetch = lambda p, q: _resp(403, {}, {"X-RateLimit-Remaining": "0"})  # noqa: E731
    with pytest.raises(RateLimited):
        list(GitHubClient(REF, "tok", fetch=fetch).pull_requests())


def test_403_with_quota_left_is_a_scope_problem():
    fetch = lambda p, q: _resp(403, {}, {"X-RateLimit-Remaining": "42"})  # noqa: E731
    with pytest.raises(AuthenticationFailed):
        list(GitHubClient(REF, "tok", fetch=fetch).pull_requests())


def test_missing_repo_raises_not_found():
    with pytest.raises(RepositoryNotFound):
        list(GitHubClient(REF, "tok", fetch=lambda p, q: _resp(404, {})).pull_requests())


def test_an_unexpected_status_falls_back_to_the_base_error():
    from specharness_adapters.github import classify
    from specharness_core.ports.repository import RepositoryError

    error = classify(500, "acme/tool")

    assert type(error) is RepositoryError
    assert "acme/tool" in str(error)


def test_error_message_never_contains_the_token():
    with pytest.raises(AuthenticationFailed) as excinfo:
        list(
            GitHubClient(REF, "ghp_super_secret", fetch=lambda p, q: _resp(401, {})).pull_requests()
        )

    assert "ghp_super_secret" not in str(excinfo.value)


# --- o fetch httpx real monta o header bearer (métrica 3) ------------------


def test_httpx_fetch_sends_a_bearer_token(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers, params):
            captured["url"] = url
            captured["headers"] = headers
            return _resp(200, [])

    monkeypatch.setattr("specharness_adapters.github.client.httpx.Client", FakeClient)

    list(GitHubClient(REF, "tok123").pull_requests())

    assert captured["headers"]["Authorization"] == "Bearer tok123"
    assert "acme/tool" in captured["url"]
