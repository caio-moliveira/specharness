"""The Jira client (SPEC-019, todos os cenários + métricas 1/2/3).

Hermetic: the `fetch` callable is injected. The happy paths run over CASSETTES
recorded against a real Jira Cloud instance (`tests/cassettes/jira/*.json` —
see the adapter README to re-record); auth, rate limit, pagination-by-token and
sprint payloads use canned pages (the real instance has no agile sprints, so
sprint cases are synthetic and marked as such). The token never reaches an
error message.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from specharness_adapters.jira import JiraClient
from specharness_core.ports.tracker import (
    InvalidTrackerConfig,
    TrackerAuthenticationFailed,
    TrackerError,
    TrackerRateLimited,
)

CASSETTES = Path(__file__).parent / "cassettes" / "jira"


def _cassette(name):
    return json.loads((CASSETTES / name).read_text(encoding="utf-8"))


def _resp(status, body, headers=None):
    return SimpleNamespace(status_code=status, json=lambda: body, headers=headers or {})


class FakeJira:
    """Routes fetches by method/path over cassettes or canned pages."""

    def __init__(self, fields=None, pages=None, transitions=None):
        self.fields = fields if fields is not None else []
        self.pages = pages or [{"issues": [], "isLast": True}]
        self.transitions = transitions or {"transitions": []}
        self.calls: list = []
        self._page = 0

    def fetch(self, method, path, params, json_body):
        # Copia os params: o cliente pode reusar o dict entre páginas.
        self.calls.append((method, path, dict(params) if params else params, json_body))
        if method == "GET" and path == "/rest/api/3/field":
            return _resp(200, self.fields)
        if method == "GET" and path == "/rest/api/3/search/jql":
            page = self.pages[self._page]
            self._page = min(self._page + 1, len(self.pages) - 1)
            return _resp(200, page)
        if method == "GET" and path.endswith("/transitions"):
            return _resp(200, self.transitions)
        if method == "POST" and path.endswith("/transitions"):
            return _resp(204, {})
        return _resp(404, {})


def _client(fake, **kw):
    return JiraClient("https://jira.ex", "u@example.com", "token", "SAM1", fetch=fake.fetch, **kw)


SPRINT_FIELDS = [
    {
        "id": "customfield_10020",
        "name": "Sprint",
        "schema": {"custom": "com.pyxis.greenhopper.jira:gh-sprint"},
    }
]


# --- cassettes reais: import + preservação de extras (métrica 3) ------------


def test_imports_the_recorded_page_as_canonical_workitems():
    fake = FakeJira(fields=_cassette("fields.json"), pages=[_cassette("search_sam1.json")])

    items = list(_client(fake).work_items())

    assert len(items) == 10
    assert {i.kind for i in items} == {"task", "epic"}  # taxonomia real gravada
    assert all(i.origin == "jira" for i in items)
    assert all(i.ref == f"jira:{i.kind}:{i.external_id}" for i in items)
    assert all(i.state in {"To Do", "In Progress", "In Review", "Done"} for i in items)
    assert all(i.url == f"https://jira.ex/browse/{i.external_id}" for i in items)
    # A instância real não tem agile sprints: todo item é backlog (cenário 2).
    assert all(i.sprint is None for i in items)


def test_every_filled_noncanonical_field_of_the_cassette_lands_in_extras():
    """Métrica 3: 100% dos campos preenchidos sem equivalente canônico preservados."""
    cassette = _cassette("search_sam1.json")
    fake = FakeJira(fields=_cassette("fields.json"), pages=[cassette])

    items = {i.external_id: i for i in _client(fake).work_items()}

    for issue in cassette["issues"]:
        extras = items[issue["key"]].extras
        for field, value in issue["fields"].items():
            if field in ("summary", "issuetype", "status"):
                continue
            if value is None or value == "" or value == [] or value == {}:
                assert field not in extras
            else:
                assert extras[field] == value, f"campo {field} descartado"


# --- cenário 1 (sintético — a instância real não tem sprints) ---------------


def test_a_story_in_an_active_sprint_gets_the_candidate_sprint():
    issue = {
        "key": "SAM1-99",
        "fields": {
            "summary": "Story com sprint",
            "issuetype": {"name": "Story"},
            "status": {"name": "To Do"},
            "customfield_10020": [{"id": 7, "name": "Sprint 7", "state": "active"}],
            "customfield_10050": "custom preenchido",
        },
    }
    fake = FakeJira(fields=SPRINT_FIELDS, pages=[{"issues": [issue], "isLast": True}])

    (item,) = list(_client(fake).work_items())

    assert item.kind == "story"
    assert item.sprint == "Sprint 7"
    assert item.extras["customfield_10050"] == "custom preenchido"
    assert "customfield_10020" not in item.extras  # sprint tem lar canônico


# --- paginação por nextPageToken --------------------------------------------


def test_paginates_until_the_token_runs_out():
    def issue(n):
        return {
            "key": f"SAM1-{n}",
            "fields": {"summary": f"I{n}", "issuetype": {"name": "Task"}, "status": {"name": "X"}},
        }

    fake = FakeJira(
        pages=[
            {"issues": [issue(1), issue(2)], "nextPageToken": "t2"},
            {"issues": [issue(3)], "isLast": True},
        ]
    )

    items = list(_client(fake, page_size=2).work_items())

    assert [i.external_id for i in items] == ["SAM1-1", "SAM1-2", "SAM1-3"]
    searches = [p for (m, p, params, j) in fake.calls if p == "/rest/api/3/search/jql"]
    assert len(searches) == 2
    tokens = [params.get("nextPageToken") for (m, p, params, j) in fake.calls if p == searches[0]]
    assert tokens == [None, "t2"]


# --- cenário 3: mudança externa de status entre imports ---------------------


def test_an_external_status_change_shows_up_on_the_next_import():
    def page(state):
        return {
            "issues": [
                {
                    "key": "SAM1-9",
                    "fields": {
                        "summary": "S",
                        "issuetype": {"name": "Task"},
                        "status": {"name": state},
                    },
                }
            ],
            "isLast": True,
        }

    before = list(_client(FakeJira(pages=[page("To Do")])).work_items())
    after = list(_client(FakeJira(pages=[page("In Progress")])).work_items())

    assert before[0].ref == after[0].ref  # mesma identidade: atualiza, não duplica
    assert before[0].state == "To Do"
    assert after[0].state == "In Progress"


# --- cenário 4 (write-back só de status, cassette real) ---------------------


def test_update_status_posts_only_a_transition():
    fake = FakeJira(transitions=_cassette("transitions_sam1_9.json"))

    _client(fake).update_status("SAM1-9", "In Progress")

    posts = [(p, j) for (m, p, params, j) in fake.calls if m == "POST"]
    assert posts == [("/rest/api/3/issue/SAM1-9/transitions", {"transition": {"id": "21"}})]
    # ADR-020: nenhuma outra escrita — summary/description são intocáveis.
    assert all(m == "GET" for (m, p, params, j) in fake.calls[:-1])


def test_update_status_matches_the_status_name_case_insensitively():
    fake = FakeJira(transitions=_cassette("transitions_sam1_9.json"))

    _client(fake).update_status("SAM1-9", "in progress")

    posts = [j for (m, p, params, j) in fake.calls if m == "POST"]
    assert posts == [{"transition": {"id": "21"}}]


def test_update_status_unreachable_by_the_workflow_is_a_config_error():
    fake = FakeJira(transitions=_cassette("transitions_sam1_9.json"))

    with pytest.raises(InvalidTrackerConfig) as excinfo:
        _client(fake).update_status("SAM1-9", "Inexistente")

    assert "status_map" in str(excinfo.value)


# --- cenário 5: credencial inválida nomeia JIRA_TOKEN -----------------------


def test_invalid_auth_names_jira_token():
    with pytest.raises(TrackerAuthenticationFailed) as excinfo:
        list(
            JiraClient(
                "https://j.ex", "u@e.com", "bad-token", "P", fetch=lambda *a: _resp(401, {})
            ).work_items()
        )

    assert "JIRA_TOKEN" in str(excinfo.value)
    assert "bad-token" not in str(excinfo.value)


# --- rate limit -------------------------------------------------------------


def test_a_rate_limited_request_is_retried_after_backoff():
    seq = iter(
        [
            _resp(429, {}, {"Retry-After": "0.2"}),
            _resp(200, {"issues": [], "isLast": True}),
        ]
    )
    sleeps: list = []

    def fetch(method, path, params, json_body):
        if path == "/rest/api/3/field":
            return _resp(200, [])
        return next(seq)

    list(
        JiraClient(
            "https://j.ex", "u@e.com", "t", "P", fetch=fetch, sleep=sleeps.append
        ).work_items()
    )

    assert sleeps == [0.2]


def test_an_abusive_retry_after_is_capped():
    seq = iter(
        [
            _resp(429, {}, {"Retry-After": "3600"}),
            _resp(200, {"issues": [], "isLast": True}),
        ]
    )
    sleeps: list = []

    def fetch(method, path, params, json_body):
        if path == "/rest/api/3/field":
            return _resp(200, [])
        return next(seq)

    list(
        JiraClient(
            "https://j.ex", "u@e.com", "t", "P", fetch=fetch, sleep=sleeps.append
        ).work_items()
    )

    assert sleeps == [30.0]  # backoff limitado, nunca 1h


def test_a_persistent_rate_limit_raises_rate_limited():
    with pytest.raises(TrackerRateLimited):
        list(
            JiraClient(
                "https://j.ex",
                "u@e.com",
                "t",
                "P",
                fetch=lambda *a: _resp(429, {}),
                sleep=lambda s: None,
                max_retries=1,
            ).work_items()
        )


# --- métrica 1: 300 issues em < 30s (medida, não afirmada) ------------------


def test_importing_300_issues_stays_under_30s():
    def issue(n):
        return {
            "key": f"SAM1-{n}",
            "fields": {
                "summary": f"Issue {n}",
                "issuetype": {"name": "Task"},
                "status": {"name": "To Do"},
                "labels": ["a", "b"],
                "customfield_10020": [{"id": 1, "name": "Sprint 1", "state": "active"}],
                "customfield_10050": {"value": n},
            },
        }

    pages = [
        {"issues": [issue(n) for n in range(start, start + 100)], "nextPageToken": f"t{start}"}
        for start in range(0, 200, 100)
    ]
    pages.append({"issues": [issue(n) for n in range(200, 300)], "isLast": True})
    fake = FakeJira(fields=SPRINT_FIELDS, pages=pages)

    started = time.perf_counter()
    items = list(_client(fake).work_items())
    elapsed = time.perf_counter() - started

    assert len(items) == 300
    assert all(i.sprint == "Sprint 1" for i in items)  # custo do sprint entra na medição
    assert elapsed < 30.0, f"import de 300 issues levou {elapsed:.1f}s"


# --- métrica 2: ciclo import -> mudança -> sync sem divergência -------------


def test_full_cycle_import_change_sync_has_zero_divergence(gateway):
    from specharness_adapters.db import WorkItemStore

    def page(state):
        return {
            "issues": [
                {
                    "key": "SAM1-9",
                    "fields": {
                        "summary": "S",
                        "issuetype": {"name": "Task"},
                        "status": {"name": state},
                    },
                }
            ],
            "isLast": True,
        }

    gateway.migrate()
    store = WorkItemStore(gateway.target)

    first = store.sync("jira", list(_client(FakeJira(pages=[page("To Do")])).work_items()))
    changed = store.sync("jira", list(_client(FakeJira(pages=[page("In Progress")])).work_items()))
    again = store.sync("jira", list(_client(FakeJira(pages=[page("In Progress")])).work_items()))

    assert (first.new_items, first.updated_items) == (1, 0)
    assert (changed.new_items, changed.updated_items) == (0, 1)  # atualizou, não duplicou
    assert again.was_noop  # 0 divergências restantes


# --- fetch httpx real: Basic auth e falha de rede (cenário 6) ---------------


def test_httpx_fetch_uses_basic_auth_email_token(monkeypatch):
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured["auth"] = kwargs.get("auth")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def request(self, method, url, params, json):
            captured["url"] = url
            if url.endswith("/field"):
                return _resp(200, [])
            return _resp(200, {"issues": [], "isLast": True})

    monkeypatch.setattr("specharness_adapters.jira.client.httpx.Client", FakeClient)

    list(JiraClient("https://j.ex", "eu@ex.com", "tok123", "P").work_items())

    assert isinstance(captured["auth"], httpx.BasicAuth)


def test_a_network_failure_tells_the_user_to_retry(monkeypatch):
    class BoomClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def request(self, method, url, params, json):
            raise httpx.ConnectError("sem rota")

    monkeypatch.setattr("specharness_adapters.jira.client.httpx.Client", BoomClient)

    with pytest.raises(TrackerError) as excinfo:
        list(JiraClient("https://j.ex", "eu@ex.com", "secreto", "P").work_items())

    message = str(excinfo.value)
    assert "rede" in message.lower()
    assert "tente de novo" in message.lower()
    assert "secreto" not in message


def test_origin_is_jira():
    assert _client(FakeJira()).origin == "jira"
