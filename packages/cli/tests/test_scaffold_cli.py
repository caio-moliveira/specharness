"""Scaffolding do harness via `specharness init` (SPEC-023)."""

from __future__ import annotations

import os
import subprocess

from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()


def _init_args(agent: str = "claude-code") -> list[str]:
    return [
        "init",
        "-y",
        "--tracker",
        "jira",
        "--git",
        "github",
        "--db",
        "sqlite",
        "--agent",
        agent,
        "--llm",
        "anthropic",
    ]


def _git(args: list[str], cwd) -> subprocess.CompletedProcess[str]:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(cwd),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True)


def test_init_writes_instruction_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, _init_args())
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()  # camada do claude-code
    assert (tmp_path / "specs" / "README.md").is_file()
    assert "Readiness Gate" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_init_gives_codex_its_own_layer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, _init_args("codex"))
    assert (tmp_path / "CODEX.md").is_file()
    assert not (tmp_path / "CLAUDE.md").exists()


def test_installed_hook_blocks_commit_without_trailer(tmp_path, monkeypatch):
    _git(["init"], tmp_path)
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, _init_args())

    hook = tmp_path / ".git" / "hooks" / "commit-msg"
    assert hook.is_file() and os.access(hook, os.X_OK)

    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    _git(["add", "."], tmp_path)
    blocked = _git(["commit", "-m", "feat: sem trailer"], tmp_path)
    assert blocked.returncode != 0  # hook barrou

    passed = _git(["commit", "-m", "feat: com trailer\n\nSpec: SPEC-001"], tmp_path)
    assert passed.returncode == 0  # com trailer, passou
