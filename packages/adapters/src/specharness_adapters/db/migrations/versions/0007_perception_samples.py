"""perception_samples: camada-3 micro-survey responses (SPEC-014, ADR-008).

One row per merged PR — a response or a skip — anchored to spec/runtime/model and
never to a respondent.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "perception_samples",
        sa.Column("pr_ref", sa.String(length=255), nullable=False),
        sa.Column("spec_id", sa.String(length=32), nullable=False),
        sa.Column("sprint", sa.String(length=128), nullable=False),
        sa.Column("runtime", sa.String(length=128), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("skipped", sa.Boolean(), nullable=False),
        sa.Column("aproveitamento", sa.Integer(), nullable=True),
        sa.Column("retrabalho", sa.String(length=16), nullable=True),
        sa.Column("tempo_percebido", sa.String(length=16), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("pr_ref"),
    )


def downgrade() -> None:
    op.drop_table("perception_samples")
