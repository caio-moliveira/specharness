"""The zero-config path, end to end (SPEC-004, critério 1).

Not parametrized: this is the SQLite-specific promise of ADR-002 — the user who
configures nothing gets a working database in a predictable place.
"""

from __future__ import annotations

from pathlib import Path

from specharness_adapters.db import gateway_from_env
from specharness_core.ports.database import DATABASE_URL_ENV


def test_default_path_creates_the_database_under_the_project_root(tmp_path):
    gateway = gateway_from_env(env={}, project_root=tmp_path)

    gateway.migrate()

    assert (tmp_path / ".specharness" / "specharness.db").is_file()


def test_default_path_does_not_require_the_directory_to_exist(tmp_path):
    """Zero perguntas inclui não pedir que o usuário crie a pasta."""
    assert not (tmp_path / ".specharness").exists()

    gateway_from_env(env={}, project_root=tmp_path).migrate()

    assert (tmp_path / ".specharness").is_dir()


def test_default_path_is_scoped_per_project(tmp_path):
    """Dois repositórios não compartilham banco (decisão E2 da spec)."""
    first, second = tmp_path / "repo-a", tmp_path / "repo-b"
    first.mkdir()
    second.mkdir()

    gateway_from_env(env={}, project_root=first).migrate()
    gateway_from_env(env={}, project_root=second).migrate()

    assert (first / ".specharness" / "specharness.db").is_file()
    assert (second / ".specharness" / "specharness.db").is_file()


def test_gateway_from_env_reads_the_real_environment_when_not_told(tmp_path, monkeypatch):
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    monkeypatch.chdir(tmp_path)

    gateway = gateway_from_env()

    assert gateway.target.is_default is True
    assert Path(gateway.target.sqlite_path or "").parent.name == ".specharness"


def test_explicit_env_var_overrides_the_default(tmp_path):
    elsewhere = (tmp_path / "outro.db").as_posix()

    gateway = gateway_from_env(
        env={DATABASE_URL_ENV: f"sqlite:///{elsewhere}"}, project_root=tmp_path
    )
    gateway.migrate()

    assert (tmp_path / "outro.db").is_file()
    assert not (tmp_path / ".specharness").exists()
    assert gateway.target.is_default is False


def test_ensure_storage_is_a_noop_for_postgres(tmp_path):
    """Postgres é do usuário: não criamos nada no servidor dele."""
    gateway = gateway_from_env(
        env={DATABASE_URL_ENV: "postgresql://u:p@host/db"}, project_root=tmp_path
    )

    gateway.ensure_storage()

    assert list(tmp_path.iterdir()) == []
