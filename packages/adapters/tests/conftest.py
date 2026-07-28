"""Backends under test (SPEC-004, métrica 2).

The contract suite runs against every backend available to the run: SQLite
always, Postgres whenever the harness is told where one is. The *product* still
knows a single switch, `SPECHARNESS_DATABASE_URL` — the extra variable here is
the test harness saying where its Postgres lives, because the SQLite cases must
keep running in the same session.
"""

from __future__ import annotations

import os

import pytest
from specharness_adapters.db import SqlAlchemyDatabaseGateway
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from sqlalchemy import create_engine, text

POSTGRES_URL_ENV = "SPECHARNESS_TEST_POSTGRES_URL"


def _backends() -> list[str]:
    backends = ["sqlite"]
    if os.environ.get(POSTGRES_URL_ENV, "").strip():
        backends.append("postgresql")
    return backends


def _wipe_postgres(url: str) -> None:
    """A clean slate: the contract asserts what a from-scratch migration does.

    The whole schema is recreated, not just the version tables: dropping only
    schema_meta/alembic_version left the domain tables behind, so the FIRST
    test to migrate poisoned the database and every later from-scratch
    migration hit DuplicateTable ("relation commits already exists") — the CI
    Postgres half was red on main because of exactly this.
    """
    engine = create_engine(url, future=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA public CASCADE"))
            connection.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


@pytest.fixture(params=_backends())
def gateway(request, tmp_path) -> SqlAlchemyDatabaseGateway:
    """A gateway on a virgin database, one per available backend."""
    if request.param == "sqlite":
        env = {DATABASE_URL_ENV: ""}
        target = resolve_database_target(env, project_root=tmp_path)
    else:
        url = os.environ[POSTGRES_URL_ENV]
        target = resolve_database_target({DATABASE_URL_ENV: url}, project_root=tmp_path)
        _wipe_postgres(target.sync_url)
    return SqlAlchemyDatabaseGateway(target)
