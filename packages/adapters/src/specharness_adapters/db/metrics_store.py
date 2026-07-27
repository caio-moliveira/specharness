"""Persistence of camada-2 metric snapshots (SPEC-013, ADR-008).

Append-only series: `record` inserts the snapshot under the next `series` number
for its sprint; nothing is ever updated in place. A recomputation — even a
correction to a formula — becomes a new series, and every earlier series stays
readable, which is what makes the determinism check meaningful (recompute and
compare, without clobbering the original)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from specharness_core.metrics import HygieneSignal, SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DatabaseTarget
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import MetricSnapshotRow


def _to_payload(snapshot: SprintSnapshot) -> dict:
    return {
        "sprint": snapshot.sprint,
        "specs": [asdict(spec) for spec in snapshot.specs],
        "hygiene": [asdict(signal) for signal in snapshot.hygiene],
    }


def _from_payload(payload: dict) -> SprintSnapshot:
    return SprintSnapshot(
        sprint=payload["sprint"],
        specs=tuple(SpecMetrics(**spec) for spec in payload["specs"]),
        hygiene=tuple(HygieneSignal(**signal) for signal in payload["hygiene"]),
    )


class MetricSnapshotStore:
    """Implements the append-only snapshot series over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def record(self, snapshot: SprintSnapshot, at: datetime) -> int:
        """Persist `snapshot` as the next series for its sprint; return the series."""
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                current = session.scalar(
                    select(func.max(MetricSnapshotRow.series)).where(
                        MetricSnapshotRow.sprint == snapshot.sprint
                    )
                )
                series = (current or 0) + 1
                session.add(
                    MetricSnapshotRow(
                        sprint=snapshot.sprint,
                        series=series,
                        payload=_to_payload(snapshot),
                        created_at=at,
                    )
                )
                session.commit()
                return series
        finally:
            engine.dispose()

    def latest(self, sprint: str) -> SprintSnapshot | None:
        """The most recent series for a sprint — the dashboard's single query."""
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                row = session.scalars(
                    select(MetricSnapshotRow)
                    .where(MetricSnapshotRow.sprint == sprint)
                    .order_by(MetricSnapshotRow.series.desc())
                    .limit(1)
                ).first()
                return _from_payload(row.payload) if row is not None else None
        finally:
            engine.dispose()

    def all_series(self, sprint: str) -> list[tuple[int, SprintSnapshot]]:
        """Every series for a sprint, oldest first — the append-only audit trail."""
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(
                    select(MetricSnapshotRow)
                    .where(MetricSnapshotRow.sprint == sprint)
                    .order_by(MetricSnapshotRow.series)
                )
                return [(row.series, _from_payload(row.payload)) for row in rows]
        finally:
            engine.dispose()
