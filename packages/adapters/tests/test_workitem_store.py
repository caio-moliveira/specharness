"""The WorkItem store's upsert (SPEC-007, métricas 2 e 3).

Runs against a real (virgin, tmp) SQLite migrated to head. Idempotency and the
status-change capture are measured here, not asserted.
"""

from __future__ import annotations

import pytest
from specharness_adapters.db import SqlAlchemyDatabaseGateway, WorkItemStore
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.tracker import WorkItem
from sqlalchemy import create_engine, text


@pytest.fixture
def store_and_target(tmp_path):
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(target).migrate()  # 0001 + 0002 + 0003
    return WorkItemStore(target), target


def _wi(external_id="1", kind="issue", state="New", title="t", sprint=None, extras=None):
    return WorkItem(
        origin="redmine",
        external_id=external_id,
        kind=kind,
        title=title,
        state=state,
        sprint=sprint,
        extras=extras or {},
    )


def _scalar(target, sql):
    engine = create_engine(target.sync_url, future=True)
    try:
        with engine.connect() as conn:
            return conn.execute(text(sql)).scalar()
    finally:
        engine.dispose()


def test_first_import_inserts_everything(store_and_target):
    store, _ = store_and_target

    result = store.sync("redmine", [_wi("1"), _wi("2")])

    assert result.new_items == 2
    assert result.updated_items == 0
    assert result.total_items == 2
    assert result.was_noop is False


def test_reimport_of_unchanged_items_is_a_noop(store_and_target):
    store, _ = store_and_target
    items = [_wi("1"), _wi("2")]
    store.sync("redmine", items)

    second = store.sync("redmine", items)

    assert second.new_items == 0
    assert second.updated_items == 0
    assert second.was_noop is True


def test_a_status_change_is_captured_as_an_update(store_and_target):
    store, target = store_and_target
    store.sync("redmine", [_wi("1", state="New")])

    result = store.sync("redmine", [_wi("1", state="Fechada")])

    assert result.new_items == 0
    assert result.updated_items == 1
    assert result.total_items == 1
    assert _scalar(target, "SELECT state FROM work_items WHERE external_id = '1'") == "Fechada"


def test_issue_and_version_with_the_same_id_are_distinct_rows(store_and_target):
    store, _ = store_and_target

    result = store.sync("redmine", [_wi("5", kind="issue"), _wi("5", kind="version")])

    assert result.new_items == 2
    assert result.total_items == 2


def test_extras_are_persisted(store_and_target):
    store, target = store_and_target

    store.sync("redmine", [_wi("1", extras={"orgao": "TCE"})])

    assert "TCE" in str(_scalar(target, "SELECT extras FROM work_items WHERE external_id = '1'"))


def test_duplicate_refs_within_one_batch_insert_once(store_and_target):
    store, _ = store_and_target

    result = store.sync("redmine", [_wi("1"), _wi("1")])

    assert result.new_items == 1
    assert result.total_items == 1
