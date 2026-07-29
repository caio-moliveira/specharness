"""The contract the LiteLLM client must satisfy (SPEC-005, critérios 2, 3, A3).

Hermetic by construction: the completion callable is injected, so every
assertion runs with no network and no key — the same way the SQLite half of the
database contract needs no server. A real provider is exercised separately,
gated on a key being present (see `test_llm_real_provider.py`).
"""

from __future__ import annotations

from types import SimpleNamespace

import litellm
import pytest
from specharness_adapters.llm import LiteLlmClient, Ping, check_connection
from specharness_core.config import RoutingConfig
from specharness_core.ports.llm import LLMClient, LLMTarget, ProviderUnreachable

COST = 0.000123


def fake_completion(*, model, messages, response_format=None, stream=False, **kwargs):
    """A canned, valid structured response — records nothing, needs nothing."""
    content = Ping(ok=True, message="pong").model_dump_json()
    message = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice], _hidden_params={"response_cost": COST})


def _client(completion=fake_completion, *, model="anthropic/claude-3-5-sonnet-latest"):
    target = LLMTarget("anthropic", model, None, "ANTHROPIC_API_KEY")
    return LiteLlmClient(target, {"ANTHROPIC_API_KEY": "sk-test"}, completion_fn=completion)


# --- satisfaz a porta do core (critério 7 análogo) -------------------------


def test_client_satisfies_the_core_port():
    assert isinstance(_client(), LLMClient)


# --- structured output validado por Pydantic (critério 2) ------------------


def test_structured_returns_a_validated_model():
    out = _client().structured("oi", Ping)

    assert isinstance(out, Ping)
    assert out.ok is True
    assert out.message == "pong"


def test_complete_returns_plain_text():
    assert "pong" in _client().complete("oi")


# --- relatório do llm test: modelo, latência, custo (critério 2) -----------


def test_test_reports_model_latency_and_cost():
    report = _client().test()

    assert report.model == "anthropic/claude-3-5-sonnet-latest"
    assert report.provider == "anthropic"
    assert report.latency_s >= 0.0
    assert report.cost_usd == pytest.approx(COST)
    assert "US$" in report.cost_label


def test_cost_is_none_when_the_model_cannot_be_priced():
    def unpriced(*, model, messages, response_format=None, stream=False, **kwargs):
        content = Ping(ok=True, message="ok").model_dump_json()
        choice = SimpleNamespace(message=SimpleNamespace(content=content))
        return SimpleNamespace(choices=[choice])  # no _hidden_params, no price

    report = _client(unpriced).test()

    assert report.cost_usd is None
    assert report.cost_label == "n/d"


# --- a key vai para a litellm mas nunca para o alvo (métrica 3) ------------


def test_the_api_key_is_passed_to_litellm_but_never_stored_on_the_target():
    captured: dict = {}

    def capture(*, model, messages, response_format=None, stream=False, **kwargs):
        captured.update(kwargs)
        content = Ping(ok=True, message="ok").model_dump_json()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    client = _client(capture)
    client.complete("oi")

    assert captured["api_key"] == "sk-test"
    assert "sk-test" not in repr(client.target)


# --- base_url alcança a chamada (critério A4) ------------------------------


def test_base_url_reaches_the_completion_call():
    captured: dict = {}

    def capture(*, model, messages, response_format=None, stream=False, **kwargs):
        captured.update(kwargs)
        content = Ping(ok=True, message="ok").model_dump_json()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    target = LLMTarget(
        "azure", "azure/gpt-4o", "https://corp.openai.azure.com", "AZURE_OPENAI_API_KEY"
    )
    LiteLlmClient(target, {"AZURE_OPENAI_API_KEY": "k"}, completion_fn=capture).complete("oi")

    assert captured["base_url"] == "https://corp.openai.azure.com"


def test_azure_api_version_reaches_the_completion_call():
    # O roteamento azure do litellm exige api_version; ela tem de chegar na chamada
    # (SPEC-027), não só ficar no .env.
    captured: dict = {}

    def capture(*, model, messages, response_format=None, stream=False, **kwargs):
        captured.update(kwargs)
        content = Ping(ok=True, message="ok").model_dump_json()
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    target = LLMTarget(
        "azure",
        "azure/deploy",
        "https://corp.openai.azure.com",
        "AZURE_OPENAI_API_KEY",
        "2024-06-01",
    )
    LiteLlmClient(target, {"AZURE_OPENAI_API_KEY": "k"}, completion_fn=capture).complete("oi")

    assert captured["api_version"] == "2024-06-01"


# --- fallback quando o default falha em runtime (critério A3) --------------


def test_fallback_model_is_used_when_the_default_fails():
    calls: list[str] = []

    def failing_default(*, model, messages, response_format=None, stream=False, **kwargs):
        calls.append(model)
        if model.startswith("anthropic"):
            raise litellm.APIConnectionError(message="down", llm_provider="anthropic", model=model)
        content = Ping(ok=True, message="via fallback").model_dump_json()
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            _hidden_params={"response_cost": 0.0},
        )

    routing = RoutingConfig(
        default="anthropic/claude-3-5-sonnet-latest", fallback="ollama/llama3.2"
    )
    env = {"ANTHROPIC_API_KEY": "x", "OLLAMA_BASE_URL": "http://localhost:11434"}

    report = check_connection(env, routing=routing, completion_fn=failing_default)

    assert report.model == "ollama/llama3.2"
    assert calls[0].startswith("anthropic")
    assert calls[1].startswith("ollama")


def test_without_a_fallback_the_failure_propagates():
    def always_fail(*, model, messages, response_format=None, stream=False, **kwargs):
        raise litellm.APIConnectionError(message="down", llm_provider="anthropic", model=model)

    routing = RoutingConfig(default="anthropic/claude-3-5-sonnet-latest")

    with pytest.raises(ProviderUnreachable):
        check_connection({"ANTHROPIC_API_KEY": "x"}, routing=routing, completion_fn=always_fail)


# --- streaming -------------------------------------------------------------


def test_stream_yields_text_chunks():
    def streamer(*, model, messages, response_format=None, stream=False, **kwargs):
        for piece in ("po", "ng"):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=piece))])

    assert "".join(_client(streamer).stream("oi")) == "pong"
