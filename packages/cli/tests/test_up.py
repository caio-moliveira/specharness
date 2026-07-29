"""Comando `specharness up` (SPEC-021): preflight de banco + boot numa porta."""

from __future__ import annotations

from specharness_cli import main
from specharness_cli.main import app
from specharness_core.ports.database import DatabaseError
from typer.testing import CliRunner

runner = CliRunner()


def test_up_help_mentions_port():
    result = runner.invoke(app, ["up", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output


def test_up_aborts_when_db_unavailable(monkeypatch):
    def boom():
        raise DatabaseError("Falha de banco em localhost. Verifique SPECHARNESS_DATABASE_URL.")

    started: list[tuple[str, int]] = []
    monkeypatch.setattr(main, "gateway_from_env", boom)
    monkeypatch.setattr(main, "_run_server", lambda host, port: started.append((host, port)))

    result = runner.invoke(app, ["up"])
    assert result.exit_code == 1
    assert not started  # o servidor nunca sobe com banco indisponível
    assert "init" in result.output.lower()


def test_up_starts_server_when_db_ok(monkeypatch):
    class _Gateway:
        def migrate(self) -> None:
            return None

    started: list[tuple[str, int]] = []
    monkeypatch.setattr(main, "gateway_from_env", lambda: _Gateway())
    monkeypatch.setattr(main, "_run_server", lambda host, port: started.append((host, port)))

    result = runner.invoke(app, ["up", "--port", "9999"])
    assert result.exit_code == 0
    assert started == [("127.0.0.1", 9999)]
