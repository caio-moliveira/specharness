"""A CLI não pode quebrar num console Windows cp1252 (regressão, SPEC-002).

O bug: `connect db` funcionava e estourava UnicodeEncodeError ao imprimir o
`✓` final, porque o stdout padrão do Windows codifica em cp1252. O fix
reconfigura stdout/stderr para UTF-8 no callback do app. Estes testes capturam
a saída num stream cp1252 de verdade — sem o fix, o primeiro falha com a
exceção original.

Nota: com o fix ativo os bytes emitidos são UTF-8 e o runner os decodifica
como cp1252, então glifos multi-byte viram mojibake no `result.output` — as
asserções ficam em substrings ASCII e em exit code/exceção, nunca no glifo.
"""

from __future__ import annotations

import pytest
from specharness_cli.main import app
from specharness_core.ports.database import DATABASE_URL_ENV
from typer.testing import CliRunner

runner_cp1252 = CliRunner(charset="cp1252")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    monkeypatch.delenv(DATABASE_URL_ENV, raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "specs").mkdir()
    return tmp_path


def test_connect_db_succeeds_on_a_cp1252_console(clean_env):
    result = runner_cp1252.invoke(app, ["connect", "db"])

    assert result.exception is None, repr(result.exception)
    assert result.exit_code == 0, result.output
    assert "Conectado" in result.output


def test_error_path_reaches_the_user_on_cp1252(clean_env):
    result = runner_cp1252.invoke(app, ["ready", "SPEC-999"])

    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit)
    assert "encontrada" in result.output


def test_status_map_renders_on_cp1252(clean_env):
    result = runner_cp1252.invoke(app, ["status"])

    assert result.exception is None, repr(result.exception)
    assert result.exit_code == 0, result.output
    assert "connect db" in result.output
