"""Persistence of perception micro-survey responses (SPEC-014, ADR-008).

One row per PR: `has_response` lets the caller honour "sem re-prompt no mesmo PR"
(a response *or* a skip counts), and the read side returns only what the pure
aggregate needs — samples and a skip count, never a respondent (there is no
respondent column to return)."""

from __future__ import annotations

from datetime import datetime

from specharness_core.perception import PerceptionSample
from specharness_core.ports.database import DatabaseTarget
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import PerceptionSampleRow


class PerceptionStore:
    """Implements the perception-sample store over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def has_response(self, pr_ref: str) -> bool:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                return session.get(PerceptionSampleRow, pr_ref) is not None
        finally:
            engine.dispose()

    def record_sample(self, sample: PerceptionSample, at: datetime) -> None:
        self._insert(
            PerceptionSampleRow(
                pr_ref=sample.pr_ref,
                spec_id=sample.spec_id,
                sprint=sample.sprint,
                runtime=sample.runtime,
                model=sample.model,
                skipped=False,
                aproveitamento=sample.aproveitamento,
                retrabalho=sample.retrabalho,
                tempo_percebido=sample.tempo_percebido,
                comentario=sample.comentario,
                created_at=at,
            )
        )

    def record_skip(
        self, pr_ref: str, spec_id: str, sprint: str, runtime: str, model: str, at: datetime
    ) -> None:
        self._insert(
            PerceptionSampleRow(
                pr_ref=pr_ref,
                spec_id=spec_id,
                sprint=sprint,
                runtime=runtime,
                model=model,
                skipped=True,
                created_at=at,
            )
        )

    def samples_for_sprint(self, sprint: str) -> list[PerceptionSample]:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                rows = session.scalars(
                    select(PerceptionSampleRow)
                    .where(
                        PerceptionSampleRow.sprint == sprint,
                        PerceptionSampleRow.skipped.is_(False),
                    )
                    .order_by(PerceptionSampleRow.pr_ref)
                )
                return [
                    PerceptionSample(
                        pr_ref=row.pr_ref,
                        spec_id=row.spec_id,
                        sprint=row.sprint,
                        runtime=row.runtime,
                        model=row.model,
                        aproveitamento=row.aproveitamento,  # type: ignore[arg-type]
                        retrabalho=row.retrabalho,  # type: ignore[arg-type]
                        tempo_percebido=row.tempo_percebido,  # type: ignore[arg-type]
                        comentario=row.comentario,
                    )
                    for row in rows
                ]
        finally:
            engine.dispose()

    def skips_for_sprint(self, sprint: str) -> int:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                count = session.scalar(
                    select(func.count())
                    .select_from(PerceptionSampleRow)
                    .where(
                        PerceptionSampleRow.sprint == sprint,
                        PerceptionSampleRow.skipped.is_(True),
                    )
                )
                return int(count or 0)
        finally:
            engine.dispose()

    def _insert(self, row: PerceptionSampleRow) -> None:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                session.add(row)
                session.commit()
        finally:
            engine.dispose()
