"""Database port — connection contract for the onboarding (SPEC-004).

Pure domain (ADR-001): no SQLAlchemy, no driver, no filesystem access. What
lives here are *decisions*, not effects — which target we resolve to, whether a
URL is usable at all, and what a failure is allowed to print. SPEC-004 requires
a malformed URL to be rejected before any connection attempt, which is only
possible if that judgement lives outside the adapter.

ADR-002 fixes the policy: SQLite is the default with zero questions asked, and
`SPECHARNESS_DATABASE_URL` is the single switch to Postgres. ADR-010 fixes the
drivers: async on the server, sync on the CLI, over the same models — so one
resolved target has to yield both URLs.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import PurePath
from typing import Protocol, runtime_checkable
from urllib.parse import urlsplit, urlunsplit

DATABASE_URL_ENV = "SPECHARNESS_DATABASE_URL"

#: Per-repository, not per-user: specharness is scoped to a project (it reads
#: `specs/` and the local git), so two repos must not share one database.
DEFAULT_SQLITE_DIR = ".specharness"
DEFAULT_SQLITE_FILENAME = "specharness.db"

#: Base schemes we speak. `postgres` is the alias most providers hand out.
_POSTGRES_SCHEMES = frozenset({"postgresql", "postgres"})
_SQLITE_SCHEMES = frozenset({"sqlite"})
SUPPORTED_SCHEMES = _POSTGRES_SCHEMES | _SQLITE_SCHEMES

_REDACTED = "***"

_SYNC_DRIVERS = {"postgresql": "postgresql+psycopg", "sqlite": "sqlite"}
_ASYNC_DRIVERS = {"postgresql": "postgresql+asyncpg", "sqlite": "sqlite+aiosqlite"}


class DatabaseError(Exception):
    """Base of every connection failure the user can act on.

    Every subclass names `SPECHARNESS_DATABASE_URL` in its message: the whole
    point of the error is to tell the user which knob to turn.
    """

    #: Filled by subclasses; `for_target` composes it with the safe URL.
    template = "Falha de banco de dados em {safe_url}. Verifique {env}."

    @classmethod
    def for_target(cls, safe_url: str, detail: str = "") -> DatabaseError:
        """Build the user-facing message. `safe_url` must already be redacted."""
        message = cls.template.format(safe_url=safe_url, env=DATABASE_URL_ENV)
        return cls(f"{message} ({detail})" if detail else message)


class ConnectionRefused(DatabaseError):
    template = (
        "Não foi possível conectar ao banco em {safe_url}. "
        "Verifique se o servidor está no ar e se {env} aponta para o host e a porta certos."
    )


class AuthenticationFailed(DatabaseError):
    template = (
        "Falha de autenticação no banco em {safe_url}. Verifique o usuário e a senha em {env}."
    )


class DatabaseNotFound(DatabaseError):
    template = (
        "O banco de dados não existe em {safe_url}. Crie-o no servidor ou ajuste o nome em {env}."
    )


class DriverMissing(DatabaseError):
    template = (
        "Driver de banco ausente para conectar em {safe_url}. "
        "Instale o driver correspondente ou ajuste o esquema em {env}."
    )


class InvalidDatabaseUrl(DatabaseError):
    """Raised before any I/O: the URL cannot describe a database we speak."""

    template = "URL inválida em {env}: {safe_url}"

    @classmethod
    def because(cls, reason: str, safe_url: str = "") -> InvalidDatabaseUrl:
        suffix = f" ({safe_url})" if safe_url else ""
        return cls(f"URL inválida em {DATABASE_URL_ENV}: {reason}.{suffix}")


@dataclass(frozen=True)
class DatabaseTarget:
    """A resolved, usable database target.

    Holding both URLs is deliberate: ADR-010 runs an async engine on the server
    and a sync one on the CLI over the same models, and the user only ever
    supplies one URL.
    """

    sync_url: str
    async_url: str
    dialect: str
    is_default: bool
    sqlite_path: PurePath | None = None

    @property
    def safe_sync_url(self) -> str:
        return redact_password(self.sync_url)


@dataclass(frozen=True)
class MigrationResult:
    """Outcome of `migrate()`. Empty `applied` is the idempotent second run."""

    revision: str
    applied: tuple[str, ...] = ()

    @property
    def was_noop(self) -> bool:
        return not self.applied


@runtime_checkable
class DatabaseGateway(Protocol):
    """What an adapter must provide for the onboarding to work."""

    @property
    def target(self) -> DatabaseTarget: ...

    def healthcheck(self) -> None:
        """Connect and prove the database answers, or raise a DatabaseError."""
        ...

    def migrate(self) -> MigrationResult:
        """Bring the schema to head. Must be idempotent (SPEC-004, critério 3)."""
        ...


def redact_password(url: str) -> str:
    """Return `url` with the password removed.

    Defensive by construction: the redacted URL is rebuilt from parsed parts,
    so neither the plain nor the percent-encoded secret can survive. A URL we
    cannot parse never raises — redaction is a safety net, and a safety net
    that throws is worse than none.
    """
    try:
        parts = urlsplit(url)
        password = parts.password
    except ValueError:
        return "<url ilegível>"
    if not password:
        return url

    userinfo = f"{parts.username}:{_REDACTED}" if parts.username else _REDACTED
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, f"{userinfo}@{host}", parts.path, parts.query, parts.fragment))


def default_sqlite_path(project_root: str | PurePath) -> PurePath:
    """Where the zero-config database lives, relative to the project root."""
    return PurePath(project_root) / DEFAULT_SQLITE_DIR / DEFAULT_SQLITE_FILENAME


def resolve_database_target(env: Mapping[str, str], project_root: str | PurePath) -> DatabaseTarget:
    """Resolve the database target from the environment.

    No I/O happens here, which is what lets SPEC-004 promise that a malformed
    URL is rejected *before* a connection is attempted.
    """
    raw = env.get(DATABASE_URL_ENV, "")
    if not raw.strip():
        return _sqlite_target(default_sqlite_path(project_root), is_default=True)
    return _target_from_url(raw.strip())


def _sqlite_target(path: PurePath, *, is_default: bool) -> DatabaseTarget:
    # A POSIX absolute path already starts with "/", which supplies SQLAlchemy's
    # fourth slash; a Windows path ("C:/...") correctly keeps three.
    location = path.as_posix()
    return DatabaseTarget(
        sync_url=f"{_SYNC_DRIVERS['sqlite']}:///{location}",
        async_url=f"{_ASYNC_DRIVERS['sqlite']}:///{location}",
        dialect="sqlite",
        is_default=is_default,
        sqlite_path=path,
    )


def _target_from_url(url: str) -> DatabaseTarget:
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise InvalidDatabaseUrl.because(f"não foi possível interpretar a URL ({exc})") from exc

    scheme = parts.scheme.lower()
    if not scheme:
        raise InvalidDatabaseUrl.because(
            "falta o esquema (esperado algo como 'postgresql://usuario@host/banco')"
        )

    # `postgresql+asyncpg` — the user may paste a driver; the base scheme decides.
    base = scheme.split("+", 1)[0]
    if base not in SUPPORTED_SCHEMES:
        supported = ", ".join(sorted(SUPPORTED_SCHEMES))
        raise InvalidDatabaseUrl.because(
            f"esquema '{base}' não é suportado (suportados: {supported})"
        )

    if base in _SQLITE_SCHEMES:
        location = parts.path.lstrip("/")
        if not location:
            raise InvalidDatabaseUrl.because("falta o caminho do arquivo SQLite")
        return _sqlite_target(PurePath(location), is_default=False)

    if not parts.hostname:
        raise InvalidDatabaseUrl.because("falta o host", safe_url=redact_password(url))
    if not parts.path.strip("/"):
        raise InvalidDatabaseUrl.because("falta o nome do banco", safe_url=redact_password(url))

    # Everything after the scheme is preserved verbatim: credentials, port,
    # database and query string are the user's, only the driver is ours.
    _, _, rest = url.partition("://")
    return DatabaseTarget(
        sync_url=f"{_SYNC_DRIVERS['postgresql']}://{rest}",
        async_url=f"{_ASYNC_DRIVERS['postgresql']}://{rest}",
        dialect="postgresql",
        is_default=False,
    )
