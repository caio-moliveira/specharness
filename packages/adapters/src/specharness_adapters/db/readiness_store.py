"""Persistence for the LLM Readiness Gate (SPEC-011).

`ReadinessCacheStore` keys evaluations by content hash so an unchanged spec is
served without a model call (critério 5, métrica 3). `OverrideStore` is the
append-only audit trail of Tech Lead overrides (critério 3).
"""

from __future__ import annotations

from datetime import datetime

from specharness_core.assessment import Evaluation, Override, ReadinessIssue
from specharness_core.ports.database import DatabaseTarget
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .models import ReadinessCacheRow, ReadinessOverrideRow


class ReadinessCacheStore:
    """Read/write cache of LLM evaluations keyed by content hash."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def get(self, content_hash: str) -> Evaluation | None:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                row = session.get(ReadinessCacheRow, content_hash)
                if row is None:
                    return None
                return Evaluation(
                    score=row.score,
                    issues=tuple(ReadinessIssue.model_validate(i) for i in row.issues),
                    model=row.model,
                    cost_usd=row.cost_usd,
                    cached=True,
                )
        finally:
            engine.dispose()

    def put(self, content_hash: str, evaluation: Evaluation, at: datetime) -> None:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                session.merge(
                    ReadinessCacheRow(
                        content_hash=content_hash,
                        score=evaluation.score,
                        issues=[issue.model_dump() for issue in evaluation.issues],
                        model=evaluation.model,
                        cost_usd=evaluation.cost_usd,
                        created_at=at,
                    )
                )
                session.commit()
        finally:
            engine.dispose()


class OverrideStore:
    """Append-only audit trail of gate overrides."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def record(self, override: Override) -> None:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                session.add(
                    ReadinessOverrideRow(
                        spec_id=override.spec_id,
                        author=override.author,
                        justification=override.justification,
                        created_at=datetime(override.at.year, override.at.month, override.at.day),
                    )
                )
                session.commit()
        finally:
            engine.dispose()

    def all_for(self, spec_id: str) -> list[Override]:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(
                    select(ReadinessOverrideRow)
                    .where(ReadinessOverrideRow.spec_id == spec_id)
                    .order_by(ReadinessOverrideRow.created_at)
                )
                return [
                    Override(
                        spec_id=row.spec_id,
                        author=row.author,
                        justification=row.justification,
                        at=row.created_at.date(),
                    )
                    for row in rows
                ]
        finally:
            engine.dispose()
