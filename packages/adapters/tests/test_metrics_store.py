"""Append-only metric snapshot series (SPEC-013, ADR-008)."""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_adapters.db import MetricSnapshotStore, SqlAlchemyDatabaseGateway
from specharness_core import HygieneSignal, SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target


@pytest.fixture
def target(tmp_path):
    resolved = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(resolved).migrate()
    return resolved


def _snapshot(sprint: str, rate: float | None) -> SprintSnapshot:
    return SprintSnapshot(
        sprint=sprint,
        specs=(
            SpecMetrics(
                spec_id="SPEC-013",
                cycle_time_seconds=100.0,
                first_run_pass_rate=rate,
                iterations_to_green=2,
                turnover_30d=0.1,
                turnover_90d=0.2,
                turnover_ratio_30d=1.0,
                turnover_ratio_90d=1.5,
                commits=7,
            ),
        ),
        hygiene=(HygieneSignal("SPEC-013", "naked-skip", "x"),),
    )


def test_record_round_trips_the_snapshot(target):
    store = MetricSnapshotStore(target)
    snap = _snapshot("2026-A4", 0.9)

    store.record(snap, datetime(2026, 7, 27))

    assert store.latest("2026-A4") == snap  # value equality across serialization


def test_first_series_is_one_and_increments(target):
    store = MetricSnapshotStore(target)
    assert store.record(_snapshot("2026-A4", 0.9), datetime(2026, 7, 27)) == 1
    assert store.record(_snapshot("2026-A4", 0.95), datetime(2026, 7, 28)) == 2


def test_a_correction_is_a_new_series_and_never_overwrites(target):
    store = MetricSnapshotStore(target)
    original = _snapshot("2026-A4", 0.90)
    corrected = _snapshot("2026-A4", 0.42)  # a recalculated value

    store.record(original, datetime(2026, 7, 27))
    store.record(corrected, datetime(2026, 7, 28))

    series = store.all_series("2026-A4")
    assert [s for s, _ in series] == [1, 2]
    assert series[0][1] == original  # original series intact
    assert series[1][1] == corrected
    assert store.latest("2026-A4") == corrected


def test_series_are_isolated_per_sprint(target):
    store = MetricSnapshotStore(target)
    store.record(_snapshot("2026-A4", 0.9), datetime(2026, 7, 27))
    assert store.record(_snapshot("2026-A5", 0.9), datetime(2026, 7, 27)) == 1
    assert store.latest("2026-A9") is None
    assert store.all_series("2026-A9") == []
