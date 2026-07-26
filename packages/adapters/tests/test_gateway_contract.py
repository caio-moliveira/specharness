"""The contract every backend must satisfy (SPEC-004, critérios 1, 2, 3).

Parametrized by the `gateway` fixture: identical assertions against SQLite and,
when the harness has one, Postgres. That the two share every line of this file
*is* métrica 2 — swapping backends changes an environment variable, not code.
"""

from __future__ import annotations

import time

import pytest
from specharness_core.ports.database import DatabaseGateway, MigrationResult
from sqlalchemy import create_engine, inspect

MAX_MIGRATION_SECONDS = 10.0


def _inspector_tables(gateway) -> list[str]:
    engine = create_engine(gateway.target.sync_url, future=True)
    try:
        return inspect(engine).get_table_names()
    finally:
        engine.dispose()


# --- migração do zero (critérios 1 e 2) ------------------------------------


def test_virgin_database_starts_with_no_revision(gateway):
    assert gateway.current_revision() is None


def test_migration_from_scratch_reaches_head(gateway):
    result = gateway.migrate()

    assert isinstance(result, MigrationResult)
    assert result.revision == "0001"
    assert result.applied == ("0001",)
    assert result.was_noop is False


def test_migration_creates_the_declared_schema(gateway):
    gateway.migrate()

    tables = _inspector_tables(gateway)
    assert "schema_meta" in tables
    assert "alembic_version" in tables


def test_migration_from_scratch_stays_under_the_budget(gateway):
    """Métrica 3: medida com perf_counter, não afirmada."""
    started = time.perf_counter()
    gateway.migrate()
    elapsed = time.perf_counter() - started

    assert elapsed < MAX_MIGRATION_SECONDS, f"migração levou {elapsed:.2f}s"


# --- idempotência (critério 3) ---------------------------------------------


def test_second_migration_is_a_noop(gateway):
    first = gateway.migrate()

    second = gateway.migrate()

    assert second.was_noop is True
    assert second.applied == ()
    assert second.revision == first.revision


def test_revision_is_unchanged_after_a_second_migration(gateway):
    gateway.migrate()
    before = gateway.current_revision()

    gateway.migrate()

    assert gateway.current_revision() == before


def test_migrating_repeatedly_never_duplicates_the_schema(gateway):
    for _ in range(3):
        gateway.migrate()

    assert _inspector_tables(gateway).count("schema_meta") == 1


# --- conectividade nos dois mundos (ADR-010) -------------------------------


def test_healthcheck_passes_on_a_migrated_database(gateway):
    gateway.migrate()

    gateway.healthcheck()  # não levanta


def test_healthcheck_works_before_any_migration(gateway):
    """Conectar e migrar são passos distintos do onboarding."""
    gateway.healthcheck()


@pytest.mark.asyncio
async def test_async_engine_reaches_the_same_database(gateway):
    """ADR-010: mesma URL resolvida, engine async do server."""
    gateway.migrate()

    await gateway.healthcheck_async()


# --- o gateway satisfaz a porta do core (critério 7) -----------------------


def test_gateway_satisfies_the_core_port(gateway):
    assert isinstance(gateway, DatabaseGateway)


def test_gateway_exposes_the_resolved_target(gateway):
    assert gateway.target.sync_url
    assert gateway.target.async_url
    assert gateway.target.dialect in {"sqlite", "postgresql"}
