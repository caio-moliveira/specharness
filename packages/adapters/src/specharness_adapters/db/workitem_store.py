"""Idempotent persistence of canonical WorkItems (SPEC-007, métricas 2 e 3).

Unlike commits and PRs (append-only), a WorkItem changes — chiefly its status.
So this store upserts by (origin, external_id): a new item is inserted, an
existing one whose fields changed is updated in place (capturing status changes
on an incremental sync), and an unchanged re-import touches nothing.
"""

from __future__ import annotations

from specharness_core.ports.database import DatabaseTarget
from specharness_core.ports.tracker import ImportResult, WorkItem
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from .models import WorkItemRow


class WorkItemStore:
    """Implements the core `WorkItemStore` port over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    def sync(self, origin: str, items: list[WorkItem]) -> ImportResult:
        engine = create_engine(self._target.sync_url, future=True)
        try:
            with Session(engine) as session:
                existing = {
                    row.ref: row
                    for row in session.scalars(
                        select(WorkItemRow).where(WorkItemRow.origin == origin)
                    )
                }
                seen: set[str] = set()
                new = updated = 0
                for item in items:
                    if item.ref in seen:
                        continue
                    seen.add(item.ref)
                    row = existing.get(item.ref)
                    if row is None:
                        session.add(_row_from(origin, item))
                        new += 1
                    elif _differs(row, item):
                        _apply(row, item)
                        updated += 1
                session.flush()
                total = session.scalar(
                    select(func.count())
                    .select_from(WorkItemRow)
                    .where(WorkItemRow.origin == origin)
                )
                session.commit()
            return ImportResult(new_items=new, updated_items=updated, total_items=total or 0)
        finally:
            engine.dispose()


def _row_from(origin: str, item: WorkItem) -> WorkItemRow:
    return WorkItemRow(
        ref=item.ref,
        origin=origin,
        external_id=item.external_id,
        kind=item.kind,
        title=item.title,
        state=item.state,
        sprint=item.sprint,
        url=item.url,
        extras=dict(item.extras),
    )


def _apply(row: WorkItemRow, item: WorkItem) -> None:
    row.kind = item.kind
    row.title = item.title
    row.state = item.state
    row.sprint = item.sprint
    row.url = item.url
    row.extras = dict(item.extras)


def _differs(row: WorkItemRow, item: WorkItem) -> bool:
    return (
        row.kind != item.kind
        or row.title != item.title
        or row.state != item.state
        or row.sprint != item.sprint
        or row.url != item.url
        or row.extras != dict(item.extras)
    )
