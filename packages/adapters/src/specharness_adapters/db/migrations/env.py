"""Alembic environment — driven by the resolved target, never by alembic.ini.

The URL always arrives from `specharness_core.ports.database`, so `alembic
upgrade head` and `specharness connect db` can never disagree about which
database they are touching. Migrations run on the sync engine in both worlds
(ADR-010): schema changes are not a place for concurrency.
"""

from __future__ import annotations

from alembic import context
from specharness_adapters.db.models import Base
from sqlalchemy import engine_from_config, pool

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if not url:  # pragma: no cover - the gateway always sets it
        raise RuntimeError("sqlalchemy.url não foi definida pelo gateway")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot ALTER in place; batch mode keeps future migrations
            # portable across both targets (ADR-002).
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():  # pragma: no cover - exercised via `alembic -x offline`
    run_migrations_offline()
else:
    run_migrations_online()
