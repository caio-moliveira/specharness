"""readiness_cache and readiness_overrides: the LLM gate's memory (SPEC-011).

The cache keys an evaluation by content hash so an unchanged spec is not
re-evaluated (critério 5). The overrides table is the audit trail for Tech Lead
overrides (critério 3), append-only.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "readiness_cache",
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("issues", sa.JSON(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("content_hash"),
    )
    op.create_table(
        "readiness_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("spec_id", sa.String(length=32), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("readiness_overrides")
    op.drop_table("readiness_cache")
