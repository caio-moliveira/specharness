"""Tests for the database port — pure resolution and redaction (SPEC-004).

The port owns the decisions that must happen *before* any I/O: which URL we
target, whether it is even usable, and what a failure is allowed to say out
loud. Everything here runs without a database.
"""

import pytest
from specharness_core.ports.database import (
    DATABASE_URL_ENV,
    SUPPORTED_SCHEMES,
    AuthenticationFailed,
    ConnectionRefused,
    DatabaseError,
    DatabaseNotFound,
    DriverMissing,
    InvalidDatabaseUrl,
    MigrationResult,
    default_sqlite_path,
    redact_password,
    resolve_database_target,
)

PROJECT_ROOT = "/srv/projeto"
PG_URL = "postgresql://joao:s3nh4-secreta@db.interno:5432/specharness"


# --- caminho default (critério 1) -----------------------------------------


def test_no_env_resolves_to_project_local_sqlite():
    target = resolve_database_target({}, project_root=PROJECT_ROOT)

    assert target.dialect == "sqlite"
    assert target.is_default is True
    assert target.sqlite_path is not None
    assert target.sqlite_path.as_posix().endswith(".specharness/specharness.db")


def test_default_sqlite_lives_under_the_given_project_root():
    target = resolve_database_target({}, project_root="/outro/lugar")

    assert target.sqlite_path is not None
    assert target.sqlite_path.as_posix() == "/outro/lugar/.specharness/specharness.db"


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_env_var_falls_back_to_the_default_path(blank):
    """Uma env var vazia é ausência de configuração, não configuração inválida."""
    target = resolve_database_target({DATABASE_URL_ENV: blank}, project_root=PROJECT_ROOT)

    assert target.is_default is True
    assert target.dialect == "sqlite"


def test_default_target_drives_both_engines():
    target = resolve_database_target({}, project_root=PROJECT_ROOT)

    assert target.sync_url.startswith("sqlite:///")
    assert target.async_url.startswith("sqlite+aiosqlite:///")


# --- Postgres do usuário (critério 2) --------------------------------------


def test_postgres_url_is_accepted_and_not_default():
    target = resolve_database_target({DATABASE_URL_ENV: PG_URL}, project_root=PROJECT_ROOT)

    assert target.dialect == "postgresql"
    assert target.is_default is False
    assert target.sqlite_path is None


def test_postgres_target_drives_both_engines_with_the_declared_drivers():
    """ADR-010: asyncpg no server, driver sync no CLI — a partir da MESMA url."""
    target = resolve_database_target({DATABASE_URL_ENV: PG_URL}, project_root=PROJECT_ROOT)

    assert target.sync_url.startswith("postgresql+psycopg://")
    assert target.async_url.startswith("postgresql+asyncpg://")


def test_postgres_alias_scheme_is_accepted():
    """`postgres://` é o que a maioria dos provedores entrega colado."""
    target = resolve_database_target(
        {DATABASE_URL_ENV: "postgres://joao:pw@host/db"}, project_root=PROJECT_ROOT
    )

    assert target.dialect == "postgresql"


def test_user_supplied_driver_is_normalized_not_trusted():
    """Se o usuário colar +asyncpg, a engine sync ainda tem que funcionar."""
    target = resolve_database_target(
        {DATABASE_URL_ENV: "postgresql+asyncpg://joao:pw@host/db"}, project_root=PROJECT_ROOT
    )

    assert target.sync_url.startswith("postgresql+psycopg://")
    assert target.async_url.startswith("postgresql+asyncpg://")


def test_credentials_and_host_survive_driver_normalization():
    target = resolve_database_target({DATABASE_URL_ENV: PG_URL}, project_root=PROJECT_ROOT)

    for url in (target.sync_url, target.async_url):
        assert "joao:s3nh4-secreta@db.interno:5432" in url
        assert url.endswith("/specharness")


# --- URL inválida rejeitada antes de qualquer I/O (critério 5) -------------


@pytest.mark.parametrize(
    "bad_url",
    [
        "mysql://user:pw@host/db",
        "mongodb://host/db",
        "redis://host:6379",
        "http://host/db",
    ],
)
def test_unsupported_scheme_is_rejected(bad_url):
    with pytest.raises(InvalidDatabaseUrl) as exc:
        resolve_database_target({DATABASE_URL_ENV: bad_url}, project_root=PROJECT_ROOT)

    assert "url inválida" in str(exc.value).lower()
    assert DATABASE_URL_ENV in str(exc.value)


@pytest.mark.parametrize(
    "bad_url",
    [
        "isto não é uma url",
        "://sem-esquema/db",
        "postgresql",
        "postgresql://",
    ],
)
def test_malformed_url_is_rejected(bad_url):
    with pytest.raises(InvalidDatabaseUrl):
        resolve_database_target({DATABASE_URL_ENV: bad_url}, project_root=PROJECT_ROOT)


def test_rejection_names_the_offending_scheme_so_the_user_can_fix_it():
    with pytest.raises(InvalidDatabaseUrl) as exc:
        resolve_database_target(
            {DATABASE_URL_ENV: "mysql://user:pw@host/db"}, project_root=PROJECT_ROOT
        )

    assert "mysql" in str(exc.value)


def test_rejecting_an_unsupported_scheme_never_leaks_the_password():
    with pytest.raises(InvalidDatabaseUrl) as exc:
        resolve_database_target(
            {DATABASE_URL_ENV: "mysql://joao:s3nh4-secreta@host/db"}, project_root=PROJECT_ROOT
        )

    assert "s3nh4-secreta" not in str(exc.value)


# --- senha nunca vaza (critério 6) -----------------------------------------


def test_redact_password_removes_the_password():
    assert "s3nh4-secreta" not in redact_password(PG_URL)


def test_redact_password_keeps_what_the_user_needs_to_debug():
    safe = redact_password(PG_URL)

    assert "db.interno" in safe
    assert "joao" in safe
    assert "specharness" in safe


@pytest.mark.parametrize(
    "secret",
    [
        "s3nh4-secreta",
        "p@ss:word/with#chars",
        "senha com espaço",
        "%2Fencoded%3Apass",
    ],
)
def test_redact_password_handles_passwords_that_encode_differently(secret):
    from urllib.parse import quote

    url = f"postgresql://joao:{quote(secret, safe='')}@host:5432/db"
    safe = redact_password(url)

    assert secret not in safe
    assert quote(secret, safe="") not in safe


def test_redact_password_is_a_noop_when_there_is_no_password():
    assert redact_password("sqlite:////srv/x/.specharness/specharness.db") == (
        "sqlite:////srv/x/.specharness/specharness.db"
    )


def test_redact_password_survives_a_url_it_cannot_parse():
    """Redação é defesa: entrada esquisita não pode virar exceção nova."""
    assert isinstance(redact_password("isto não é uma url"), str)


# --- toda falha aponta a env var (critério 4) ------------------------------


@pytest.mark.parametrize(
    ("error_cls", "substring"),
    [
        (ConnectionRefused, "não foi possível conectar"),
        (AuthenticationFailed, "autenticação"),
        (DatabaseNotFound, "banco de dados não existe"),
        (DriverMissing, "driver"),
    ],
)
def test_each_failure_class_carries_its_actionable_substring(error_cls, substring):
    message = str(error_cls.for_target(safe_url="postgresql://joao:***@host/db"))

    assert substring in message.lower()
    assert DATABASE_URL_ENV in message


def test_every_failure_class_derives_from_a_single_base():
    for cls in (
        ConnectionRefused,
        AuthenticationFailed,
        DatabaseNotFound,
        DriverMissing,
        InvalidDatabaseUrl,
    ):
        assert issubclass(cls, DatabaseError)


def test_failure_classes_are_distinct_so_callers_can_branch():
    classes = {ConnectionRefused, AuthenticationFailed, DatabaseNotFound, DriverMissing}

    assert len(classes) == 4


def test_invalid_url_error_never_carries_a_raw_password_through_because():
    error = InvalidDatabaseUrl.because(
        "falta o host", safe_url=redact_password("postgresql://joao:s3nh4@/db")
    )

    assert "s3nh4" not in str(error)


# --- SQLite explícito e alvos derivados -----------------------------------


def test_explicit_sqlite_url_is_accepted_but_is_not_the_default_path():
    target = resolve_database_target(
        {DATABASE_URL_ENV: "sqlite:///dados/meu.db"}, project_root=PROJECT_ROOT
    )

    assert target.dialect == "sqlite"
    assert target.is_default is False
    assert target.sqlite_path is not None
    assert target.sqlite_path.as_posix() == "dados/meu.db"


def test_sqlite_url_without_a_path_is_rejected():
    with pytest.raises(InvalidDatabaseUrl):
        resolve_database_target({DATABASE_URL_ENV: "sqlite://"}, project_root=PROJECT_ROOT)


def test_postgres_url_without_a_database_name_is_rejected():
    with pytest.raises(InvalidDatabaseUrl) as exc:
        resolve_database_target(
            {DATABASE_URL_ENV: "postgresql://joao:pw@host:5432/"}, project_root=PROJECT_ROOT
        )

    assert "banco" in str(exc.value)
    assert "pw" not in str(exc.value).replace("SPECHARNESS_DATABASE_URL", "")


def test_default_sqlite_path_is_composed_not_guessed():
    assert default_sqlite_path("/raiz").as_posix() == "/raiz/.specharness/specharness.db"


def test_safe_sync_url_is_the_redacted_one():
    target = resolve_database_target({DATABASE_URL_ENV: PG_URL}, project_root=PROJECT_ROOT)

    assert "s3nh4-secreta" not in target.safe_sync_url
    assert "db.interno" in target.safe_sync_url


def test_migration_result_reports_a_second_run_as_noop():
    assert MigrationResult(revision="0001", applied=()).was_noop is True
    assert MigrationResult(revision="0001", applied=("0001",)).was_noop is False


def test_supported_schemes_are_exactly_what_the_adrs_declare():
    """ADR-002: SQLite e Postgres. Um esquema a mais aqui é uma decisão sem ADR."""
    assert sorted(SUPPORTED_SCHEMES) == ["postgres", "postgresql", "sqlite"]
