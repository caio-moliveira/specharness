"""work_items: canonical WorkItems from trackers (SPEC-007, ADR-007).

Keyed by (origin, external_id) so a re-import updates in place instead of
duplicating. `extras` keeps every tracker field without a canonical home.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_items",
        sa.Column("ref", sa.String(length=320), nullable=False),
        sa.Column("origin", sa.String(length=64), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=128), nullable=False),
        sa.Column("sprint", sa.String(length=128), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("extras", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("ref"),
    )


def downgrade() -> None:
    op.drop_table("work_items")
