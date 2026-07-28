"""Auto-load do .env no entrypoint do CLI (SPEC-004/005 — onboarding).

O defeito de onboarding: o código lê os.environ direto e nada carregava o
.env, então `specharness connect db` funcionava só com `uv run --env-file`.
O callback do app agora carrega o .env do diretório corrente, sem nunca
sobrescrever variáveis já exportadas no shell.
"""

from __future__ import annotations

import os

from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()

SENTINEL = "SPECHARNESS_DOTENV_SENTINEL"


def test_env_file_is_loaded_from_cwd(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{SENTINEL}=do-arquivo\n", encoding="utf-8")
    monkeypatch.delenv(SENTINEL, raising=False)
    try:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert os.environ.get(SENTINEL) == "do-arquivo"
    finally:
        os.environ.pop(SENTINEL, None)


def test_shell_environment_wins_over_env_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(f"{SENTINEL}=do-arquivo\n", encoding="utf-8")
    monkeypatch.setenv(SENTINEL, "do-shell")
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert os.environ.get(SENTINEL) == "do-shell"


def test_missing_env_file_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".env").exists()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
