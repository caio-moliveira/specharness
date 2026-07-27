"""The GitHub Issues client (SPEC-008, critérios 1/2, métrica 1).

Hermetic: the `fetch` callable is injected, so pagination, the PR filter, auth
and rate limit run with no network and no token. The token is never echoed.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from specharness_adapters.github_issues import GitHubIssuesClient
from specharness_core.ports.repository import RepoRef
from specharness_core.ports.tracker import (
    TrackerAuthenticationFailed,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimited,
)

REF = RepoRef("acme", "tool")


def _resp(status, body, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: body, headers=headers or {})


def _issue(number, title="I", state="open", milestone=None, labels=(), assignees=(), **extra):
    payload: dict = {"number": number, "title": title, "state": state, "html_url": f"u/{number}"}
    if milestone:
        payload["milestone"] = {"title": milestone}
    payload["labels"] = [{"name": name} for name in labels]
    payload["assignees"] = [{"login": login} for login in assignees]
    payload.update(extra)
    return payload


class FakeIssues:
    def __init__(self, pages):
        self.pages = pages
        self.seen: list = []

    def fetch(self, path, params):
        self.seen.append((path, params["page"]))
        page = params["page"]
        body = self.pages[page - 1] if page - 1 < len(self.pages) else []
        return _resp(200, body)


def _client(fake, **kw):
    return GitHubIssuesClient(REF, "tok", fetch=fake.fetch, **kw)


# --- import com labels, milestone, assignees (critério 1, 2) ---------------


def test_imports_issues_with_labels_milestone_and_assignees():
    fake = FakeIssues(
        [[_issue(1, "Bug", "open", milestone="Sprint 1", labels=["bug", "p1"], assignees=["ana"])]]
    )

    items = list(_client(fake).work_items())

    assert len(items) == 1
    item = items[0]
    assert item.external_id == "1"
    assert item.kind == "issue"
    assert item.title == "Bug"
    assert item.state == "open"
    assert item.sprint == "Sprint 1"  # milestone -> sprint candidata
    assert item.url == "u/1"
    assert item.ref == "github:issue:1"
    assert item.extras["labels"] == ["bug", "p1"]
    assert item.extras["assignees"] == ["ana"]


def test_pull_requests_returned_by_the_issues_endpoint_are_skipped():
    fake = FakeIssues(
        [[_issue(1, "Real issue"), {"number": 2, "title": "a PR", "pull_request": {"url": "x"}}]]
    )

    items = list(_client(fake).work_items())

    assert [i.external_id for i in items] == ["1"]


def test_paginates_until_a_short_page():
    fake = FakeIssues([[_issue(1), _issue(2)], [_issue(3)]])

    items = list(_client(fake, per_page=2).work_items())

    assert [i.external_id for i in items] == ["1", "2", "3"]
    assert [page for (path, page) in fake.seen] == [1, 2]


# --- auth, rate limit, not found -------------------------------------------


def test_invalid_auth_raises_and_names_github_token():
    with pytest.raises(TrackerAuthenticationFailed) as excinfo:
        list(GitHubIssuesClient(REF, "bad", fetch=lambda p, q: _resp(401, {})).work_items())

    assert "GITHUB_TOKEN" in str(excinfo.value)


def test_rate_limited_403_raises_rate_limited():
    fetch = lambda p, q: _resp(403, {}, {"X-RateLimit-Remaining": "0"})  # noqa: E731
    with pytest.raises(TrackerRateLimited):
        list(GitHubIssuesClient(REF, "tok", fetch=fetch).work_items())


def test_403_with_quota_left_is_an_auth_problem():
    fetch = lambda p, q: _resp(403, {}, {"X-RateLimit-Remaining": "9"})  # noqa: E731
    with pytest.raises(TrackerAuthenticationFailed):
        list(GitHubIssuesClient(REF, "tok", fetch=fetch).work_items())


def test_missing_repo_raises_not_found():
    with pytest.raises(TrackerNotFound):
        list(GitHubIssuesClient(REF, "tok", fetch=lambda p, q: _resp(404, {})).work_items())


def test_the_token_never_appears_in_an_error():
    with pytest.raises(TrackerAuthenticationFailed) as excinfo:
        list(GitHubIssuesClient(REF, "ghp_secret", fetch=lambda p, q: _resp(401, {})).work_items())

    assert "ghp_secret" not in str(excinfo.value)


def test_origin_is_github():
    assert _client(FakeIssues([[]])).origin == "github"


def test_an_unexpected_status_falls_back_to_the_base_tracker_error():
    from specharness_adapters.github_issues import classify

    error = classify(500, "acme/tool")

    assert type(error) is TrackerError
    assert "acme/tool" in str(error)


# --- fetch httpx real: header e falha de rede ------------------------------


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
            captured["headers"] = headers
            return _resp(200, [])

    monkeypatch.setattr("specharness_adapters.github_issues.client.httpx.Client", FakeClient)

    list(GitHubIssuesClient(REF, "tok123").work_items())

    assert captured["headers"]["Authorization"] == "Bearer tok123"


def test_a_network_failure_becomes_a_tracker_error(monkeypatch):
    class BoomClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def get(self, url, headers, params):
            raise httpx.ConnectError("sem rota")

    monkeypatch.setattr("specharness_adapters.github_issues.client.httpx.Client", BoomClient)

    with pytest.raises(TrackerError) as excinfo:
        list(GitHubIssuesClient(REF, "secret").work_items())

    assert "secret" not in str(excinfo.value)
    assert "rede" in str(excinfo.value).lower()
