"""Comando `specharness up` (SPEC-021): preflight de banco + boot numa porta."""

from __future__ import annotations

from specharness_cli import main
from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def test_up_help_mentions_port():
    result = runner.invoke(app, ["up", "--help"])
    assert result.exit_code == 0
    assert "--port" in result.output


def test_up_aborts_when_configured_db_unreachable(monkeypatch):
    # Banco CONFIGURADO mas inacessível — connection refused real em :1, sem mock.
    monkeypatch.setenv("SPECHARNESS_DATABASE_URL", "postgresql+psycopg://u:p@127.0.0.1:1/none")
    started: list[tuple[str, int]] = []
    monkeypatch.setattr(main, "_run_server", lambda host, port: started.append((host, port)))

    result = runner.invoke(app, ["up"])
    assert result.exit_code == 1
    assert not started  # o servidor nunca sobe com banco inacessível
    assert "SPECHARNESS_DATABASE_URL" in result.output  # erro nomeia a conexão


def test_up_starts_with_sqlite_default(tmp_path, monkeypatch):
    # Sem config, ADR-002 sobe com o SQLite default zero-config — não exige init.
    monkeypatch.delenv("SPECHARNESS_DATABASE_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    started: list[tuple[str, int]] = []
    monkeypatch.setattr(main, "_run_server", lambda host, port: started.append((host, port)))

    result = runner.invoke(app, ["up", "--port", "9999"])
    assert result.exit_code == 0
    assert started == [("127.0.0.1", 9999)]
