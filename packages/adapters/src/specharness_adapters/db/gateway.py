"""SQLAlchemy gateway: connect, migrate, translate failures (SPEC-004).

One resolved target drives both engines (ADR-010) and one migration path drives
both dialects (ADR-002). Every escape route out of this module raises a
`DatabaseError` from the core port — callers never see a driver exception, and
never see a password.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from specharness_core.ports.database import (
    DatabaseError,
    DatabaseTarget,
    MigrationResult,
    resolve_database_target,
)
from sqlalchemy import Connection, create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine

from .errors import classify

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class SqlAlchemyDatabaseGateway:
    """Implements `DatabaseGateway` over SQLAlchemy 2."""

    def __init__(self, target: DatabaseTarget) -> None:
        self._target = target

    @property
    def target(self) -> DatabaseTarget:
        return self._target

    # --- storage ----------------------------------------------------------

    def ensure_storage(self) -> None:
        """Create the SQLite directory. No-op for Postgres, which the user owns.

        This is what makes the default path answer zero questions: the user
        never has to pick or create a location.
        """
        path = self._target.sqlite_path
        if path is None:
            return
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    # --- connectivity -----------------------------------------------------

    def healthcheck(self) -> None:
        """Prove the database answers, or raise a `DatabaseError`."""
        self.ensure_storage()
        try:
            engine = create_engine(self._target.sync_url, future=True)
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
            finally:
                engine.dispose()
        except Exception as exc:
            raise self._as_database_error(exc) from exc

    async def healthcheck_async(self) -> None:
        """Same proof over the async engine — the server's path (ADR-010)."""
        self.ensure_storage()
        try:
            engine = create_async_engine(self._target.async_url, future=True)
            try:
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
            finally:
                await engine.dispose()
        except Exception as exc:
            raise self._as_database_error(exc) from exc

    # --- migrations -------------------------------------------------------

    def current_revision(self) -> str | None:
        """Revision the database is on, or None if never migrated.

        Creates the SQLite directory first: on a virgin default path the file
        does not exist yet, and sqlite3 reports a missing *directory* as
        "unable to open database file" — which would surface to the user as
        "o banco de dados não existe", pointing them at a problem they do not
        have.
        """
        self.ensure_storage()
        try:
            engine = create_engine(self._target.sync_url, future=True)
            try:
                with engine.connect() as connection:
                    return self._revision_of(connection)
            finally:
                engine.dispose()
        except Exception as exc:
            raise self._as_database_error(exc) from exc

    def migrate(self) -> MigrationResult:
        """Bring the schema to head.

        Idempotent by construction (SPEC-004, critério 3): the revision is read
        before and after, and an unchanged revision reports an empty `applied`.
        """
        self.ensure_storage()
        config = self._alembic_config()
        before = self.current_revision()
        try:
            command.upgrade(config, "head")
        except Exception as exc:
            raise self._as_database_error(exc) from exc
        after = self.current_revision()

        if after is None:  # pragma: no cover - head always stamps a revision
            raise RuntimeError("migração terminou sem revisão registrada")
        return MigrationResult(revision=after, applied=self._between(config, before, after))

    def _alembic_config(self) -> Config:
        config = Config()
        # ConfigParser interpolates '%': a percent-encoded password would blow
        # up here long before it reached the driver.
        config.set_main_option("script_location", _escape(MIGRATIONS_DIR.as_posix()))
        config.set_main_option("sqlalchemy.url", _escape(self._target.sync_url))
        return config

    @staticmethod
    def _revision_of(connection: Connection) -> str | None:
        return MigrationContext.configure(connection).get_current_revision()

    @staticmethod
    def _between(config: Config, before: str | None, after: str) -> tuple[str, ...]:
        if before == after:
            return ()
        script = ScriptDirectory.from_config(config)
        return tuple(rev.revision for rev in script.iterate_revisions(after, before))

    def _as_database_error(self, exc: BaseException) -> DatabaseError:
        return classify(exc, safe_url=self._target.safe_sync_url)


def _escape(value: str) -> str:
    return value.replace("%", "%%")


def gateway_from_env(
    env: Mapping[str, str] | None = None, project_root: str | Path | None = None
) -> SqlAlchemyDatabaseGateway:
    """Build the gateway the way the CLI and the server both should.

    Resolution happens in the core (pure); only the result reaches SQLAlchemy.
    """
    target = resolve_database_target(
        os.environ if env is None else env,
        project_root=Path.cwd() if project_root is None else project_root,
    )
    return SqlAlchemyDatabaseGateway(target)
