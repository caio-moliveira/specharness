"""`specharness connect db` — the first screen of the onboarding (SPEC-004).

Métrica 1 is the load-bearing one here: the default path asks zero questions.
That is asserted twice — once by proving no prompt primitive is ever reached,
once by running with stdin closed.
"""

from __future__ import annotations

import click
import pytest
from specharness_cli.main import app
from specharness_core.ports.database import DATABASE_URL_ENV
from typer.testing import CliRunner

runner = CliRunner()

SECRET = "s3nh4-secreta"
UNREACHABLE = f"postgresql://joao:{SECRET}@127.0.0.1:1/specharness?connect_timeout=2"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def forbid_prompts(monkeypatch):
    """Any interactive primitive becomes a hard failure."""

    def explode(*args, **kwargs):
        raise AssertionError("o caminho default não pode perguntar nada ao usuário")

    monkeypatch.setattr(click, "prompt", explode)
    monkeypatch.setattr(click, "confirm", explode)
    monkeypatch.setattr(click.termui, "prompt", explode)
    monkeypatch.setattr(click.termui, "confirm", explode)


# --- caminho default, zero perguntas (critério 1, métrica 1) ---------------


def test_default_path_never_prompts(clean_env, forbid_prompts):
    result = runner.invoke(app, ["connect", "db"], input="")

    assert result.exit_code == 0, result.output
    assert (clean_env / ".specharness" / "specharness.db").is_file()


def test_default_path_succeeds_with_stdin_closed(clean_env):
    result = runner.invoke(app, ["connect", "db"], input="")

    assert result.exit_code == 0, result.output


def test_output_tells_the_user_what_was_connected(clean_env):
    result = runner.invoke(app, ["connect", "db"])

    assert "sqlite" in result.output.lower()
    assert ".specharness" in result.output


def test_output_reports_the_applied_migration(clean_env):
    result = runner.invoke(app, ["connect", "db"])

    assert "0001" in result.output


# --- idempotência pela porta do usuário (critério 3) -----------------------


def test_second_run_is_a_noop_and_still_succeeds(clean_env):
    first = runner.invoke(app, ["connect", "db"])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["connect", "db"])

    assert second.exit_code == 0, second.output
    assert "em dia" in second.output.lower()


# --- falhas (critérios 4, 5, 6) --------------------------------------------


def test_unreachable_host_exits_nonzero_with_an_actionable_message(clean_env, monkeypatch):
    monkeypatch.setenv(DATABASE_URL_ENV, UNREACHABLE)

    result = runner.invoke(app, ["connect", "db"])

    assert result.exit_code == 1
    assert DATABASE_URL_ENV in result.output
    assert "não foi possível conectar" in result.output.lower()


def test_failure_output_never_shows_the_password(clean_env, monkeypatch):
    monkeypatch.setenv(DATABASE_URL_ENV, UNREACHABLE)

    result = runner.invoke(app, ["connect", "db"])

    assert SECRET not in result.output


def test_failure_output_is_a_message_not_a_traceback(clean_env, monkeypatch):
    monkeypatch.setenv(DATABASE_URL_ENV, UNREACHABLE)

    result = runner.invoke(app, ["connect", "db"])

    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


def test_unsupported_scheme_exits_nonzero_before_connecting(clean_env, monkeypatch):
    monkeypatch.setenv(DATABASE_URL_ENV, "mysql://joao:pw@127.0.0.1:1/db")

    result = runner.invoke(app, ["connect", "db"])

    assert result.exit_code == 1
    assert "url inválida" in result.output.lower()
    assert "mysql" in result.output


def test_no_database_file_is_left_behind_when_the_url_is_invalid(clean_env, monkeypatch):
    monkeypatch.setenv(DATABASE_URL_ENV, "mysql://host/db")

    runner.invoke(app, ["connect", "db"])

    assert not (clean_env / ".specharness").exists()


# --- descoberta (o comando existe e se explica) ----------------------------


def test_connect_is_discoverable_from_the_root_help(clean_env):
    result = runner.invoke(app, ["--help"])

    assert "connect" in result.output


def test_connect_db_has_its_own_help(clean_env):
    result = runner.invoke(app, ["connect", "db", "--help"])

    assert result.exit_code == 0
    assert DATABASE_URL_ENV in result.output
