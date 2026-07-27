"""Declarative models — one definition, two engines (ADR-010).

SPEC-004 is a connection spec, not a domain-modelling spec, so the only table
here is infrastructure: `schema_meta` records which specharness created the
database and when. Domain tables arrive with the specs that need them
(SPEC-009 commits, SPEC-013 metrics) and hang off this same `Base`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for every specharness table."""


class SchemaMeta(Base):
    """Provenance of the database itself.

    Deliberately not a domain entity: it exists so `alembic upgrade head` has
    something real to create, and so a support question ("which version made
    this database?") has an answer.
    """

    __tablename__ = "schema_meta"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    specharness_version: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CommitRow(Base):
    """A commit ingested from the local git history (SPEC-006).

    Keyed by (repo, sha): the same sha in two repos is two rows, and re-ingesting
    the same commit is a no-op — that is what makes the sync idempotent (métrica
    2). `spec_trailers` is the extracted `Spec:` linking source for SPEC-009.
    """

    __tablename__ = "commits"

    repo: Mapped[str] = mapped_column(String(255), primary_key=True)
    sha: Mapped[str] = mapped_column(String(40), primary_key=True)
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    authored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    spec_trailers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)


class PullRequestRow(Base):
    """A pull request ingested from the GitHub API (SPEC-006). Keyed by (repo, number)."""

    __tablename__ = "pull_requests"

    repo: Mapped[str] = mapped_column(String(255), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    head_branch: Mapped[str] = mapped_column(String(255), nullable=False)
    base_branch: Mapped[str] = mapped_column(String(255), nullable=False)


class PullRequestCommitRow(Base):
    """The link between a pull request and a commit it carries (SPEC-006, critério 3)."""

    __tablename__ = "pull_request_commits"

    repo: Mapped[str] = mapped_column(String(255), primary_key=True)
    number: Mapped[int] = mapped_column(Integer, primary_key=True)
    sha: Mapped[str] = mapped_column(String(40), primary_key=True)


class WorkItemRow(Base):
    """A canonical WorkItem imported from a tracker (SPEC-007, ADR-007).

    Keyed by `ref` (`origin:kind:external_id`) so an issue and a version that
    happen to share a numeric id never collide. Re-importing the same item
    updates it in place (status changes — métrica 3) instead of duplicating.
    `extras` holds every tracker field without a canonical home, never discarded.
    """

    __tablename__ = "work_items"

    ref: Mapped[str] = mapped_column(String(320), primary_key=True)
    origin: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(128), nullable=False)
    sprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    extras: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
