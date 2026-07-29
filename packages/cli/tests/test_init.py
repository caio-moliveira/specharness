"""Comando `specharness init` (SPEC-022): grava config, guia .env, protege segredos."""

from __future__ import annotations

from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()

BASE = [
    "init",
    "-y",
    "--tracker",
    "jira",
    "--git",
    "github",
    "--db",
    "postgres",
    "--agent",
    "claude-code",
    "--llm",
    "anthropic",
]


def test_init_writes_config_and_scaffolds_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, BASE)
    assert result.exit_code == 0
    cfg = (tmp_path / "specharness.yaml").read_text(encoding="utf-8")
    assert "tracker: jira" in cfg
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    for name in (
        "JIRA_URL",
        "JIRA_TOKEN",
        "GITHUB_TOKEN",
        "SPECHARNESS_DATABASE_URL",
        "ANTHROPIC_API_KEY",
    ):
        assert f"{name}=" in env


def test_init_never_writes_secret_names_into_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, BASE)
    cfg = (tmp_path / "specharness.yaml").read_text(encoding="utf-8")
    for name in ("JIRA_TOKEN", "GITHUB_TOKEN", "SPECHARNESS_DATABASE_URL", "ANTHROPIC_API_KEY"):
        assert name not in cfg


def test_init_ensures_env_is_gitignored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    runner.invoke(app, BASE)
    assert ".env" in (tmp_path / ".gitignore").read_text(encoding="utf-8").splitlines()


def test_init_is_idempotent_on_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, BASE)
    before = (tmp_path / "specharness.yaml").read_text(encoding="utf-8")
    result = runner.invoke(app, BASE)
    after = (tmp_path / "specharness.yaml").read_text(encoding="utf-8")
    assert before == after
    assert "já estava atualizado" in result.output


def test_init_preserves_existing_env_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-real-value\n", encoding="utf-8")
    runner.invoke(app, BASE)
    env = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY=sk-real-value" in env  # valor real intacto
    assert env.count("ANTHROPIC_API_KEY=") == 1  # não duplicou a variável


def test_init_non_interactive_uses_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "-y"])
    assert result.exit_code == 0
    cfg = (tmp_path / "specharness.yaml").read_text(encoding="utf-8")
    assert "tracker: github-issues" in cfg  # primeira opção = default


def test_init_rejects_invalid_selection(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "-y", "--tracker", "asana"])
    assert result.exit_code == 1
    assert "asana" in result.output
