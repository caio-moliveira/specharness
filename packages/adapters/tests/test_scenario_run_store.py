"""ScenarioRun persistence (SPEC-012, first-run audit trail)."""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_adapters.db import ScenarioRunStore, SqlAlchemyDatabaseGateway
from specharness_core import ScenarioRun
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target


@pytest.fixture
def target(tmp_path):
    resolved = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(resolved).migrate()
    return resolved


def test_records_are_read_back_in_order(target):
    store = ScenarioRunStore(target)
    store.record(
        [
            ScenarioRun("SPEC-042", "c1", "passed", first_run=True),
            ScenarioRun("SPEC-042", "c2", "pending", first_run=True),
        ],
        datetime(2026, 7, 27),
    )

    runs = store.all_for("SPEC-042")

    assert [(r.scenario_title, r.status) for r in runs] == [("c1", "passed"), ("c2", "pending")]
    assert all(r.first_run for r in runs)
    assert store.all_for("SPEC-999") == []


def test_has_first_run_flips_once_a_first_run_is_recorded(target):
    store = ScenarioRunStore(target)
    assert store.has_first_run("SPEC-042") is False

    store.record([ScenarioRun("SPEC-042", "c", "passed", first_run=True)], datetime(2026, 7, 27))

    assert store.has_first_run("SPEC-042") is True


def test_a_non_first_run_does_not_set_the_flag(target):
    store = ScenarioRunStore(target)

    store.record([ScenarioRun("SPEC-042", "c", "passed", first_run=False)], datetime(2026, 7, 27))

    assert store.has_first_run("SPEC-042") is False
