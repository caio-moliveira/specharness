"""Every driver failure must land on an actionable class (SPEC-004, critério 4).

These run without a database on purpose: the mapping from "what the driver
threw" to "what the user reads" is the part that must be provable everywhere,
not only on the CI runner that has Postgres.
"""

import pytest
from specharness_adapters.db.errors import classify
from specharness_core.ports.database import (
    DATABASE_URL_ENV,
    AuthenticationFailed,
    ConnectionRefused,
    DatabaseError,
    DatabaseNotFound,
    DriverMissing,
)
from sqlalchemy.exc import ArgumentError, DBAPIError, NoSuchModuleError, OperationalError

SAFE_URL = "postgresql+psycopg://joao:***@db.interno:5432/specharness"
SECRET = "s3nh4-secreta"


class FakeDriverError(Exception):
    """Stands in for a psycopg/asyncpg error: message plus optional SQLSTATE."""

    def __init__(self, message: str, sqlstate: str | None = None):
        super().__init__(message)
        self.sqlstate = sqlstate


def operational(message: str, sqlstate: str | None = None) -> OperationalError:
    return OperationalError("SELECT 1", {}, FakeDriverError(message, sqlstate))


# --- SQLSTATE é a evidência primária ---------------------------------------


@pytest.mark.parametrize(
    ("sqlstate", "expected"),
    [
        ("28P01", AuthenticationFailed),
        ("28000", AuthenticationFailed),
        ("3D000", DatabaseNotFound),
        ("08001", ConnectionRefused),
        ("08004", ConnectionRefused),
        ("08006", ConnectionRefused),
    ],
)
def test_sqlstate_decides_the_class(sqlstate, expected):
    assert isinstance(classify(operational("erro do driver", sqlstate), SAFE_URL), expected)


# --- texto do driver é o fallback ------------------------------------------


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("connection refused", ConnectionRefused),
        ("could not connect to server", ConnectionRefused),
        ("Connection refused (0x0000274D/10061)", ConnectionRefused),
        ("timeout expired", ConnectionRefused),
        ("password authentication failed for user 'joao'", AuthenticationFailed),
        ('role "joao" does not exist', AuthenticationFailed),
        ('database "specharness" does not exist', DatabaseNotFound),
        ("unable to open database file", DatabaseNotFound),
    ],
)
def test_driver_text_decides_when_there_is_no_sqlstate(message, expected):
    assert isinstance(classify(operational(message), SAFE_URL), expected)


def test_sqlstate_wins_over_a_misleading_message():
    """Se o SQLSTATE diz autenticação, o texto não reclassifica."""
    error = classify(operational("could not connect to server", "28P01"), SAFE_URL)

    assert isinstance(error, AuthenticationFailed)


# --- driver ausente ---------------------------------------------------------


@pytest.mark.parametrize(
    "exc",
    [
        NoSuchModuleError("Can't load plugin: sqlalchemy.dialects:postgresql.pg8000"),
        ModuleNotFoundError("No module named 'psycopg'"),
        ImportError("cannot import name 'asyncpg'"),
    ],
)
def test_missing_driver_is_its_own_class(exc):
    assert isinstance(classify(exc, SAFE_URL), DriverMissing)


# --- catch-all ainda aponta a env var --------------------------------------


def test_unrecognized_failure_still_points_at_the_env_var():
    """O que a spec proíbe é a mensagem sem ponteiro, não o catch-all."""
    error = classify(operational("algo totalmente inesperado"), SAFE_URL)

    assert isinstance(error, DatabaseError)
    assert DATABASE_URL_ENV in str(error)


def test_a_plain_exception_is_wrapped_not_swallowed():
    error = classify(RuntimeError("pane geral"), SAFE_URL)

    assert isinstance(error, DatabaseError)
    assert DATABASE_URL_ENV in str(error)


def test_argument_error_from_a_bad_url_is_reported_as_such():
    error = classify(ArgumentError("Could not parse SQLAlchemy URL"), SAFE_URL)

    assert isinstance(error, DatabaseError)


# --- nenhuma classificação vaza a senha (critério 6) -----------------------


@pytest.mark.parametrize(
    "exc",
    [
        operational(f"could not connect using password {SECRET}"),
        operational(f"auth failed for postgresql://joao:{SECRET}@host/db", "28P01"),
        ModuleNotFoundError(f"No module named 'psycopg' while opening ...{SECRET}"),
        RuntimeError(f"pane com {SECRET} no meio"),
    ],
)
def test_no_classified_error_ever_prints_the_password(exc):
    """O driver pode ecoar a URL inteira; o que o usuário lê é nosso."""
    message = str(classify(exc, SAFE_URL))

    assert SECRET not in message
    assert DATABASE_URL_ENV in message


def test_classification_preserves_the_cause_for_debugging():
    original = operational("connection refused")

    error = classify(original, SAFE_URL)

    assert error.__cause__ is original


def test_every_classified_error_names_the_safe_url():
    error = classify(operational("connection refused"), SAFE_URL)

    assert "db.interno" in str(error)


def test_dbapi_error_without_orig_does_not_crash_the_classifier():
    exc = DBAPIError("SELECT 1", {}, Exception("sem sqlstate"))

    assert isinstance(classify(exc, SAFE_URL), DatabaseError)
