"""metric_snapshots: append-only camada-2 metrics series (SPEC-013, ADR-008).

Each sprint metrics computation is a new row with the next `series` number, so a
correction never overwrites an earlier snapshot.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metric_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sprint", sa.String(length=128), nullable=False),
        sa.Column("series", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("metric_snapshots")
