"""commits, pull_requests and their link: the repository tables (SPEC-006).

SPEC-006 is the first spec to bring domain data in: commit history from the
local git CLI (ADR-011) and pull requests from the GitHub API, keyed so that a
re-sync inserts nothing (métrica 2).

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "commits",
        sa.Column("repo", sa.String(length=255), nullable=False),
        sa.Column("sha", sa.String(length=40), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("spec_trailers", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("repo", "sha"),
    )
    op.create_table(
        "pull_requests",
        sa.Column("repo", sa.String(length=255), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("head_branch", sa.String(length=255), nullable=False),
        sa.Column("base_branch", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("repo", "number"),
    )
    op.create_table(
        "pull_request_commits",
        sa.Column("repo", sa.String(length=255), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("sha", sa.String(length=40), nullable=False),
        sa.PrimaryKeyConstraint("repo", "number", "sha"),
    )


def downgrade() -> None:
    op.drop_table("pull_request_commits")
    op.drop_table("pull_requests")
    op.drop_table("commits")
