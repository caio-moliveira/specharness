"""scenario_runs: the BDD verify audit trail (SPEC-012, ADR-016).

Append-only record of each scenario's outcome, with the first-run marker that
the metrics layer reads. Only CI runs are persisted here.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spec_id", sa.String(length=32), nullable=False),
        sa.Column("scenario_title", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("first_run", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("scenario_runs")
