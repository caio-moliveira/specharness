"""`specharness llm test` — the mandatory LLM screen (SPEC-005).

Hermetic: `litellm.completion` and the Ollama probe are monkeypatched, so the
command is exercised end to end without a network or a key. The load-bearing
assertions are that a real API key never reaches the output (métrica 3) and that
no provider blocks the gate while leaving the deterministic floor (cenário 3).
"""

from __future__ import annotations

from types import SimpleNamespace

import litellm
import pytest
from specharness_adapters.llm import Ping
from specharness_cli.main import app
from typer.testing import CliRunner

runner = CliRunner()

PROVIDER_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "OLLAMA_BASE_URL")
SECRET = "sk-ant-super-secret-value"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for key in PROVIDER_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _fake_completion(*, model, messages, response_format=None, stream=False, **kwargs):
    content = Ping(ok=True, message="pong").model_dump_json()
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    return SimpleNamespace(choices=[choice], _hidden_params={"response_cost": 0.00042})


@pytest.fixture
def fake_llm(monkeypatch):
    monkeypatch.setattr(litellm, "completion", _fake_completion)


@pytest.fixture
def ollama_down(monkeypatch):
    monkeypatch.setattr("specharness_adapters.llm.detect.ollama_responds", lambda base: False)


@pytest.fixture
def ollama_up(monkeypatch):
    monkeypatch.setattr("specharness_adapters.llm.detect.ollama_responds", lambda base: True)


# --- cenário 1: API key valida com structured output -----------------------


def test_api_key_path_reports_model_latency_and_cost(monkeypatch, fake_llm):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)

    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 0, result.output
    assert "anthropic" in result.output.lower()
    assert "latência" in result.output.lower()
    assert "custo" in result.output.lower()


def test_the_api_key_never_appears_in_the_output(monkeypatch, fake_llm):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)

    result = runner.invoke(app, ["llm", "test"])

    assert SECRET not in result.output


# --- cenário 2: Ollama local como caminho de custo zero --------------------


def test_ollama_is_used_when_no_key_and_it_responds(monkeypatch, fake_llm, ollama_up):
    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 0, result.output
    assert "ollama" in result.output.lower()


# --- cenário 3: nenhuma via bloqueia só o semântico ------------------------


def test_no_provider_blocks_with_guidance_for_both_paths(ollama_down):
    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 1
    assert "ANTHROPIC_API_KEY" in result.output
    assert "OLLAMA_BASE_URL" in result.output


def test_no_provider_keeps_the_deterministic_floor_explicit(ollama_down):
    result = runner.invoke(app, ["llm", "test"])

    assert "determinísticas seguem" in result.output.lower()


def test_no_provider_output_is_a_message_not_a_traceback(ollama_down):
    result = runner.invoke(app, ["llm", "test"])

    assert "Traceback" not in result.output
    assert result.exception is None or isinstance(result.exception, SystemExit)


# --- cenário 4: roteamento por tarefa lê specharness.yaml ------------------


def test_task_routing_uses_the_configured_model(monkeypatch, clean_env):
    captured: dict = {}

    def capture(*, model, messages, response_format=None, stream=False, **kwargs):
        captured["model"] = model
        content = Ping(ok=True, message="ok").model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            _hidden_params={"response_cost": 0.0},
        )

    monkeypatch.setattr(litellm, "completion", capture)
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    (clean_env / "specharness.yaml").write_text(
        "llm:\n"
        "  default: anthropic/claude-3-5-sonnet-latest\n"
        "  tasks:\n"
        "    readiness_gate: anthropic/claude-3-5-haiku-latest\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["llm", "test", "--task", "readiness_gate"])

    assert result.exit_code == 0, result.output
    assert captured["model"] == "anthropic/claude-3-5-haiku-latest"


def test_invalid_config_exits_nonzero_with_a_message(monkeypatch, clean_env, ollama_up, fake_llm):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    (clean_env / "specharness.yaml").write_text("llm:\n  tasks: {}\n", encoding="utf-8")

    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 1
    assert "specharness.yaml" in result.output


# --- critério A5: falha em runtime deixa o semântico explicitamente pendente


def test_runtime_failure_degrades_with_the_semantic_pending_note(monkeypatch, ollama_down):
    def boom(*, model, messages, response_format=None, stream=False, **kwargs):
        raise litellm.APIConnectionError(message="down", llm_provider="anthropic", model=model)

    monkeypatch.setattr(litellm, "completion", boom)
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)

    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 1
    assert "semântica pendente" in result.output.lower()
    assert "determinísticas seguem" in result.output.lower()
    assert SECRET not in result.output


# --- critério A3: o relatório mostra o modelo de fallback ------------------


def test_fallback_model_appears_in_the_report(monkeypatch, clean_env, ollama_down):
    def fail_default(*, model, messages, response_format=None, stream=False, **kwargs):
        if model.startswith("anthropic"):
            raise litellm.APIConnectionError(message="down", llm_provider="anthropic", model=model)
        content = Ping(ok=True, message="via fallback").model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            _hidden_params={"response_cost": 0.0},
        )

    monkeypatch.setattr(litellm, "completion", fail_default)
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    (clean_env / "specharness.yaml").write_text(
        "llm:\n  default: anthropic/claude-3-5-sonnet-latest\n  fallback: ollama/llama3.2\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["llm", "test"])

    assert result.exit_code == 0, result.output
    assert "ollama/llama3.2" in result.output


# --- descoberta ------------------------------------------------------------


def test_llm_is_discoverable_from_the_root_help():
    result = runner.invoke(app, ["--help"])

    assert "llm" in result.output


def test_llm_test_has_its_own_help():
    result = runner.invoke(app, ["llm", "test", "--help"])

    assert result.exit_code == 0
    assert "--task" in result.output
