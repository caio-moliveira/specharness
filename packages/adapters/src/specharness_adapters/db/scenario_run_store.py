"""Persistence of BDD scenario runs (SPEC-012, ADR-016).

Append-only: every CI run is recorded. `has_first_run` lets the caller mark the
first CI run after ready as `first_run` and never again (métrica-mãe da camada 2).
"""

from __future__ import annotations

from datetime import datetime

from specharness_core.ports.database import DatabaseTarget
from specharness_core.verify import ScenarioRun
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import ScenarioRunRow


class ScenarioRunStore:
    """Implements the scenario-run audit trail over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def has_first_run(self, spec_id: str) -> bool:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                count = session.scalar(
                    select(func.count())
                    .select_from(ScenarioRunRow)
                    .where(ScenarioRunRow.spec_id == spec_id, ScenarioRunRow.first_run.is_(True))
                )
                return bool(count)
        finally:
            engine.dispose()

    def record(self, runs: list[ScenarioRun], at: datetime) -> None:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                for run in runs:
                    session.add(
                        ScenarioRunRow(
                            spec_id=run.spec_id,
                            scenario_title=run.scenario_title,
                            status=run.status,
                            first_run=run.first_run,
                            created_at=at,
                        )
                    )
                session.commit()
        finally:
            engine.dispose()

    def all_for(self, spec_id: str) -> list[ScenarioRun]:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(
                    select(ScenarioRunRow)
                    .where(ScenarioRunRow.spec_id == spec_id)
                    .order_by(ScenarioRunRow.id)
                )
                return [
                    ScenarioRun(
                        spec_id=row.spec_id,
                        scenario_title=row.scenario_title,
                        status=row.status,  # type: ignore[arg-type]
                        first_run=row.first_run,
                    )
                    for row in rows
                ]
        finally:
            engine.dispose()
