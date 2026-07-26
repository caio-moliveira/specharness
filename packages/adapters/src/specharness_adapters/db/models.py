"""Declarative models — one definition, two engines (ADR-010).

SPEC-004 is a connection spec, not a domain-modelling spec, so the only table
here is infrastructure: `schema_meta` records which specharness created the
database and when. Domain tables arrive with the specs that need them
(SPEC-009 commits, SPEC-013 metrics) and hang off this same `Base`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
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
