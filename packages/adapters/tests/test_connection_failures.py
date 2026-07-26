"""Real failures against a real driver (SPEC-004, critérios 4, 5, 6).

`test_error_classification` proves the mapping in isolation; this file proves
the wiring — that a genuine psycopg failure travels through the gateway and
arrives as the sentence the spec promises, with the password gone.
"""

from __future__ import annotations

import pytest
from specharness_adapters.db import gateway_from_env
from specharness_core.ports.database import (
    DATABASE_URL_ENV,
    ConnectionRefused,
    DatabaseError,
    InvalidDatabaseUrl,
)
from sqlalchemy import create_engine, text

SECRET = "s3nh4-secreta"
#: Port 1 with a short timeout: nothing listens there, and the driver says so
#: fast enough to belong in the default suite.
UNREACHABLE = f"postgresql://joao:{SECRET}@127.0.0.1:1/specharness?connect_timeout=2"


@pytest.fixture
def unreachable(tmp_path):
    return gateway_from_env(env={DATABASE_URL_ENV: UNREACHABLE}, project_root=tmp_path)


@pytest.fixture(scope="module")
def refused_error() -> ConnectionRefused:
    """One real failed connection, shared by every assertion about its message.

    Each attempt costs a full `connect_timeout`; the assertions below inspect
    the *same* error, so the suite pays that once instead of six times. The
    paths that genuinely differ (migrate, async) still connect for themselves.
    """
    gateway = gateway_from_env(env={DATABASE_URL_ENV: UNREACHABLE}, project_root=".")
    with pytest.raises(ConnectionRefused) as exc:
        gateway.healthcheck()
    return exc.value


# --- host inacessível (critério 4) -----------------------------------------


def test_unreachable_host_raises_connection_refused(refused_error):
    assert isinstance(refused_error, ConnectionRefused)


def test_unreachable_host_message_points_at_the_env_var(refused_error):
    message = str(refused_error)

    assert DATABASE_URL_ENV in message
    assert "não foi possível conectar" in message.lower()


def test_migration_against_an_unreachable_host_fails_the_same_way(unreachable):
    """Migrar não pode escapar da classificação por um caminho diferente."""
    with pytest.raises(ConnectionRefused) as exc:
        unreachable.migrate()

    assert DATABASE_URL_ENV in str(exc.value)


@pytest.mark.asyncio
async def test_async_engine_classifies_failures_too(unreachable):
    with pytest.raises(ConnectionRefused):
        await unreachable.healthcheck_async()


# --- senha nunca vaza (critério 6) -----------------------------------------


def test_failure_message_never_contains_the_password(refused_error):
    assert SECRET not in str(refused_error)


def test_failure_message_keeps_host_and_database_for_debugging(refused_error):
    message = str(refused_error)

    assert "127.0.0.1" in message
    assert "specharness" in message


def test_the_whole_exception_chain_is_free_of_the_password(refused_error):
    """O traceback inteiro vai para o log de CI — não só a mensagem do topo."""
    error: BaseException | None = refused_error
    seen = 0
    while error is not None:
        assert SECRET not in str(error), f"senha vazou em {type(error).__name__}"
        seen += 1
        error = error.__cause__
    assert seen >= 2, "esperava a exceção original encadeada como causa"


# --- URL inválida rejeitada antes de qualquer I/O (critério 5) -------------


def test_unsupported_scheme_never_reaches_the_driver(tmp_path):
    with pytest.raises(InvalidDatabaseUrl):
        gateway_from_env(
            env={DATABASE_URL_ENV: "mysql://joao:pw@127.0.0.1:1/db"}, project_root=tmp_path
        )


def test_rejection_happens_at_construction_not_at_connect(tmp_path):
    """Se a URL só falhasse no connect, o critério 5 seria falso."""
    with pytest.raises(InvalidDatabaseUrl) as exc:
        gateway_from_env(env={DATABASE_URL_ENV: "mysql://host/db"}, project_root=tmp_path)

    assert "mysql" in str(exc.value)


# --- falha durante a migração, não na conexão ------------------------------


def test_a_colliding_table_fails_the_migration_with_an_actionable_error(tmp_path):
    """Banco alcançável, migração impossível: o erro ainda tem que ser nosso.

    Cenário real de quem aponta o specharness para um banco que já usa. A
    conexão funciona, então a falha nasce dentro do `alembic upgrade` — um
    caminho que a classificação precisa cobrir tanto quanto o de rede.
    """
    gateway = gateway_from_env(env={}, project_root=tmp_path)
    gateway.ensure_storage()
    engine = create_engine(gateway.target.sync_url, future=True)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE schema_meta (outra_coisa TEXT)"))
    finally:
        engine.dispose()

    with pytest.raises(DatabaseError) as exc:
        gateway.migrate()

    assert DATABASE_URL_ENV in str(exc.value)
    assert "Traceback" not in str(exc.value)
