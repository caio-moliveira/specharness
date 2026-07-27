"""End-to-end: import -> external closure -> sync (SPEC-008, métrica 2, cenário 2).

Wires the real GitHub Issues client (with an injected fetch) to the real
WorkItemStore on a tmp SQLite. Proves 0 state divergences after a full cycle:
an issue closed on GitHub becomes `closed` in the store on the next sync.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from specharness_adapters.db import SqlAlchemyDatabaseGateway, WorkItemStore
from specharness_adapters.github_issues import GitHubIssuesClient
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.repository import RepoRef
from sqlalchemy import create_engine, text

REF = RepoRef("acme", "tool")


def _resp(body):
    return SimpleNamespace(status_code=200, json=lambda: body, headers={})


def _issue(number, state):
    return {
        "number": number,
        "title": "Bug",
        "state": state,
        "html_url": f"u/{number}",
        "labels": [],
        "assignees": [],
    }


def _fetch_for(state):
    def fetch(path, params):
        return _resp([_issue(1, state)] if params["page"] == 1 else [])

    return fetch


@pytest.fixture
def store_and_target(tmp_path):
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()
    return WorkItemStore(target), target


def _state_in_db(target, external_id):
    engine = create_engine(target.sync_url, future=True)
    try:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT state FROM work_items WHERE external_id = :eid"), {"eid": external_id}
            ).scalar()
    finally:
        engine.dispose()


def test_external_closure_reflects_after_the_next_sync(store_and_target):
    store, target = store_and_target

    open_items = list(GitHubIssuesClient(REF, "tok", fetch=_fetch_for("open")).work_items())
    first = store.sync("github", open_items)
    assert first.new_items == 1
    assert _state_in_db(target, "1") == "open"

    # a issue é fechada diretamente no GitHub; o próximo sync a captura
    closed_items = list(GitHubIssuesClient(REF, "tok", fetch=_fetch_for("closed")).work_items())
    second = store.sync("github", closed_items)

    assert second.new_items == 0
    assert second.updated_items == 1  # o fechamento externo virou update
    assert _state_in_db(target, "1") == "closed"  # 0 divergências de estado
