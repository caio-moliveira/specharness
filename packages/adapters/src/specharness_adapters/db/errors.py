"""Driver failure -> actionable error (SPEC-004, critério 4).

The user never reads a psycopg traceback. They read one of five sentences, each
naming `SPECHARNESS_DATABASE_URL` and the thing they can actually change. The
translation lives here so the gateway stays about connecting, not about
guessing what went wrong.

Classification prefers SQLSTATE over message text: SQLSTATE is a contract,
driver wording is not (it changes with locale, version and platform).
"""

from __future__ import annotations

from specharness_core.ports.database import (
    AuthenticationFailed,
    ConnectionRefused,
    DatabaseError,
    DatabaseNotFound,
    DriverMissing,
)
from sqlalchemy.exc import NoSuchModuleError

#: SQLSTATE classes we can act on. Source: PostgreSQL Appendix A.
_SQLSTATE_MAP: dict[str, type[DatabaseError]] = {
    "28P01": AuthenticationFailed,  # invalid_password
    "28000": AuthenticationFailed,  # invalid_authorization_specification
    "3D000": DatabaseNotFound,  # invalid_catalog_name
    "08001": ConnectionRefused,  # sqlclient_unable_to_establish_sqlconnection
    "08004": ConnectionRefused,  # sqlserver_rejected_establishment_of_sqlconnection
    "08006": ConnectionRefused,  # connection_failure
}

#: Fallback only. Ordered: the first match wins, so the specific patterns for
#: authentication precede the broader connection ones.
_TEXT_MAP: tuple[tuple[tuple[str, ...], type[DatabaseError]], ...] = (
    (
        ("password authentication failed", "authentication failed", "does not exist\nrole"),
        AuthenticationFailed,
    ),
    (("role ", "no password supplied"), AuthenticationFailed),
    (("does not exist", "unable to open database file", "no such database"), DatabaseNotFound),
    (
        (
            "connection refused",
            "could not connect",
            "timeout",
            "timed out",
            "connection reset",
            "name or service not known",
            "host unreachable",
        ),
        ConnectionRefused,
    ),
    (("no module named", "can't load plugin", "cannot import"), DriverMissing),
)


def _driver_message(exc: BaseException) -> str:
    """Text of the underlying driver error, falling back to the wrapper."""
    orig = getattr(exc, "orig", None)
    return str(orig) if orig is not None else str(exc)


def _sqlstate(exc: BaseException) -> str | None:
    orig = getattr(exc, "orig", None)
    for candidate in (orig, exc):
        state = getattr(candidate, "sqlstate", None) or getattr(candidate, "pgcode", None)
        if isinstance(state, str) and state:
            return state
    return None


def classify(exc: BaseException, safe_url: str) -> DatabaseError:
    """Turn a driver/ORM exception into an actionable `DatabaseError`.

    `safe_url` must already be redacted — the returned message quotes it, and
    the driver's own text is never echoed (SPEC-004, critério 6): a driver is
    free to include the connection string, password and all, in what it raises.
    """
    if isinstance(exc, ImportError | NoSuchModuleError):
        return _build(DriverMissing, safe_url, exc)

    state = _sqlstate(exc)
    if state is not None and state in _SQLSTATE_MAP:
        return _build(_SQLSTATE_MAP[state], safe_url, exc)

    text = _driver_message(exc).lower()
    for needles, error_cls in _TEXT_MAP:
        if any(needle in text for needle in needles):
            return _build(error_cls, safe_url, exc)

    return _build(DatabaseError, safe_url, exc)


def _build(error_cls: type[DatabaseError], safe_url: str, cause: BaseException) -> DatabaseError:
    # `type(cause).__name__` only — never the message. The class name is enough
    # to debug and cannot carry a secret.
    error = error_cls.for_target(safe_url=safe_url, detail=type(cause).__name__)
    error.__cause__ = cause
    return error
