"""The Redmine client (SPEC-007, todos os critérios + métricas 1/2).

Hermetic: the `fetch` callable is injected, so pagination, auth, rate limit,
missing fields and the write-back all run with no network and no key. The `sleep`
of the backoff is injected too, so tests wait for nothing. The API key is never
echoed in an error.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest
from specharness_adapters.redmine import RedmineClient
from specharness_core.ports.tracker import (
    InvalidTrackerConfig,
    TrackerAuthenticationFailed,
    TrackerError,
    TrackerNotFound,
    TrackerRateLimited,
)


def _resp(status, body, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: body, headers=headers or {})


def _issue(issue_id, subject="S", status_name="New", version_name=None, **extra):
    payload = {"id": issue_id, "subject": subject, "status": {"id": 1, "name": status_name}}
    if version_name:
        payload["fixed_version"] = {"id": 9, "name": version_name}
    payload.update(extra)
    return payload


def _version(version_id, name, status="open", **extra):
    return {"id": version_id, "name": name, "status": status, **extra}


class FakeRedmine:
    """Routes fetches by method/path over canned data."""

    def __init__(self, issues=None, versions=None, statuses=None):
        self.issues = issues or []
        self.versions = versions or []
        self.statuses = statuses or []
        self.calls: list = []

    def fetch(self, method, path, params, json):
        self.calls.append((method, path, params, json))
        if method == "GET" and path == "/issues.json":
            offset, limit = params["offset"], params["limit"]
            page = self.issues[offset : offset + limit]
            return _resp(200, {"issues": page, "total_count": len(self.issues)})
        if method == "GET" and path.endswith("/versions.json"):
            return _resp(200, {"versions": self.versions})
        if method == "GET" and path == "/issue_statuses.json":
            return _resp(200, {"issue_statuses": self.statuses})
        if method == "PUT" and path.startswith("/issues/"):
            return _resp(204, {})
        return _resp(404, {})


def _client(fake, **kw):
    return RedmineClient("https://redmine.ex", "key", "proj", fetch=fake.fetch, **kw)


# --- import de issues e versions (critério 1) ------------------------------


def test_imports_issues_and_versions_as_canonical_workitems():
    fake = FakeRedmine(
        issues=[
            _issue(1, "Primeira", "New", version_name="Sprint 1"),
            _issue(2, "Segunda", "Em andamento"),
        ],
        versions=[_version(9, "Sprint 1")],
    )

    items = list(_client(fake).work_items())

    issues = [i for i in items if i.kind == "issue"]
    versions = [i for i in items if i.kind == "version"]
    assert [i.external_id for i in issues] == ["1", "2"]
    assert issues[0].title == "Primeira"
    assert issues[0].state == "New"
    assert issues[0].sprint == "Sprint 1"
    assert issues[0].url == "https://redmine.ex/issues/1"
    assert issues[0].ref == "redmine:issue:1"
    assert issues[1].sprint is None
    assert [v.title for v in versions] == ["Sprint 1"]
    assert versions[0].ref == "redmine:version:9"


# --- paginação por offset/total_count (métrica 1) --------------------------


def test_paginates_issues_by_offset_until_total_count():
    fake = FakeRedmine(issues=[_issue(i, f"I{i}") for i in range(1, 6)])  # 5 issues

    items = [i for i in _client(fake, page_size=2).work_items() if i.kind == "issue"]

    assert [i.external_id for i in items] == ["1", "2", "3", "4", "5"]
    offsets = [params["offset"] for (m, p, params, j) in fake.calls if p == "/issues.json"]
    assert offsets == [0, 2, 4]  # 3 páginas, parou ao alcançar total_count


# --- auth, not found, rate limit (critério auth, métrica 1) ----------------


def test_invalid_auth_raises_tracker_authentication_failed():
    with pytest.raises(TrackerAuthenticationFailed):
        list(
            RedmineClient(
                "https://r.ex", "bad", "proj", fetch=lambda *a: _resp(401, {})
            ).work_items()
        )


def test_missing_project_raises_not_found():
    with pytest.raises(TrackerNotFound):
        list(
            RedmineClient("https://r.ex", "k", "proj", fetch=lambda *a: _resp(404, {})).work_items()
        )


def test_a_rate_limited_request_is_retried_after_backoff():
    seq = iter(
        [
            _resp(429, {}, {"Retry-After": "0.1"}),
            _resp(200, {"issues": [_issue(1)], "total_count": 1}),
        ]
    )
    sleeps: list = []

    def fetch(method, path, params, json):
        return next(seq) if path == "/issues.json" else _resp(200, {"versions": []})

    items = [
        i
        for i in RedmineClient(
            "https://r.ex", "k", "proj", fetch=fetch, sleep=sleeps.append
        ).work_items()
        if i.kind == "issue"
    ]

    assert [i.external_id for i in items] == ["1"]
    assert sleeps == [0.1]  # respeitou Retry-After


def test_retry_after_defaults_when_the_header_is_bogus():
    seq = iter(
        [_resp(429, {}, {"Retry-After": "abc"}), _resp(200, {"issues": [], "total_count": 0})]
    )
    sleeps: list = []

    def fetch(method, path, params, json):
        return next(seq) if path == "/issues.json" else _resp(200, {"versions": []})

    list(RedmineClient("https://r.ex", "k", "proj", fetch=fetch, sleep=sleeps.append).work_items())

    assert sleeps == [1.0]


def test_a_persistent_rate_limit_raises_rate_limited():
    with pytest.raises(TrackerRateLimited):
        list(
            RedmineClient(
                "https://r.ex",
                "k",
                "proj",
                fetch=lambda *a: _resp(429, {}),
                sleep=lambda s: None,
                max_retries=1,
            ).work_items()
        )


# --- write-back de status (critério 2) -------------------------------------


def test_update_status_resolves_the_name_and_puts_the_id():
    fake = FakeRedmine(statuses=[{"id": 5, "name": "Fechada"}, {"id": 1, "name": "New"}])

    _client(fake).update_status("42", "Fechada")

    puts = [(p, j) for (m, p, params, j) in fake.calls if m == "PUT"]
    assert puts == [("/issues/42.json", {"issue": {"status_id": 5}})]


def test_update_status_with_an_unknown_status_is_a_config_error():
    fake = FakeRedmine(statuses=[{"id": 1, "name": "New"}])

    with pytest.raises(InvalidTrackerConfig):
        _client(fake).update_status("42", "Inexistente")


def test_origin_is_redmine():
    assert _client(FakeRedmine()).origin == "redmine"


def test_a_failed_put_raises(monkeypatch):
    fake = FakeRedmine(statuses=[{"id": 5, "name": "Fechada"}])

    def fetch(method, path, params, json):
        if method == "PUT":
            return _resp(422, {})
        return fake.fetch(method, path, params, json)

    client = RedmineClient("https://r.ex", "k", "proj", fetch=fetch)
    with pytest.raises(TrackerError):
        client.update_status("42", "Fechada")


# --- não-vazamento da API key (métrica 3 análoga) --------------------------


def test_error_message_never_contains_the_api_key():
    with pytest.raises(TrackerAuthenticationFailed) as excinfo:
        list(
            RedmineClient(
                "https://r.ex", "redmine-secret-key", "proj", fetch=lambda *a: _resp(401, {})
            ).work_items()
        )

    assert "redmine-secret-key" not in str(excinfo.value)


# --- fetch httpx real: header e falha de rede ------------------------------


def test_httpx_fetch_sends_the_api_key_header(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def request(self, method, url, headers, params, json):
            captured["headers"] = headers
            captured["url"] = url
            return _resp(200, {"issues": [], "total_count": 0})

    monkeypatch.setattr("specharness_adapters.redmine.client.httpx.Client", FakeClient)

    list(RedmineClient("https://r.ex", "key123", "proj").work_items())

    assert captured["headers"]["X-Redmine-API-Key"] == "key123"


def test_a_network_failure_becomes_a_tracker_error(monkeypatch):
    class BoomClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def request(self, method, url, headers, params, json):
            raise httpx.ConnectError("sem rota")

    monkeypatch.setattr("specharness_adapters.redmine.client.httpx.Client", BoomClient)

    with pytest.raises(TrackerError) as excinfo:
        list(RedmineClient("https://r.ex", "secret", "proj").work_items())

    assert "secret" not in str(excinfo.value)
    assert "rede" in str(excinfo.value).lower()
