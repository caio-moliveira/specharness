"""The LLM port's pure decisions (SPEC-005, critérios 1, 3, 4, A1, A4, A5).

No network here: resolution, routing and redaction are domain judgements, and
they are the ones SPEC-005 promises happen before any provider is reached.
"""

from __future__ import annotations

import pytest
from specharness_core.config import RoutingConfig
from specharness_core.ports.llm import (
    AZURE_API_KEY_ENV,
    AZURE_ENDPOINT_ENV,
    DEFAULT_OLLAMA_BASE_URL,
    OLLAMA_BASE_URL_ENV,
    InvalidLLMConfig,
    LLMTarget,
    NoProviderConfigured,
    available_providers,
    onboarding_status,
    resolve_llm_target,
    resolve_model_target,
)

ANTHROPIC = {"ANTHROPIC_API_KEY": "sk-ant-xxx"}


# --- resolução por ambiente (cenário 1) ------------------------------------


def test_resolves_anthropic_from_its_env_key():
    target = resolve_llm_target(ANTHROPIC)

    assert target.provider == "anthropic"
    assert target.model.startswith("anthropic/")
    assert target.api_key_env == "ANTHROPIC_API_KEY"


def test_api_key_precedence_is_anthropic_then_openai():
    env = {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "b"}

    assert resolve_llm_target(env).provider == "anthropic"


def test_no_key_falls_back_to_the_ollama_target():
    """Sem key, o alvo a *tentar* é o Ollama; a liveness é do adapter (cenário 2)."""
    target = resolve_llm_target({})

    assert target.provider == "ollama"
    assert target.base_url == DEFAULT_OLLAMA_BASE_URL
    assert target.api_key_env is None


def test_ollama_base_url_is_honored():
    target = resolve_llm_target({OLLAMA_BASE_URL_ENV: "http://gpu-box:11434"})

    assert target.provider == "ollama"
    assert target.base_url == "http://gpu-box:11434"


# --- roteamento por tarefa (cenário 4, critério 3) -------------------------


def test_routing_task_overrides_the_default_model():
    routing = RoutingConfig(
        default="anthropic/claude-3-5-sonnet-latest",
        tasks={"readiness_gate": "anthropic/claude-3-5-haiku-latest"},
    )

    routed = resolve_llm_target(ANTHROPIC, routing=routing, task="readiness_gate")
    default = resolve_llm_target(ANTHROPIC, routing=routing, task="outra_tarefa")

    assert routed.model == "anthropic/claude-3-5-haiku-latest"
    assert default.model == "anthropic/claude-3-5-sonnet-latest"


def test_routing_without_task_uses_the_default():
    routing = RoutingConfig(default="anthropic/claude-3-5-sonnet-latest")

    assert resolve_llm_target(ANTHROPIC, routing=routing).model == (
        "anthropic/claude-3-5-sonnet-latest"
    )


def test_routed_provider_without_its_key_names_the_missing_var():
    routing = RoutingConfig(default="openai/gpt-4o")

    with pytest.raises(NoProviderConfigured) as excinfo:
        resolve_llm_target({}, routing=routing)

    assert "OPENAI_API_KEY" in str(excinfo.value)


# --- base_url customizada (critério A4) ------------------------------------


def test_azure_endpoint_becomes_the_base_url():
    env = {AZURE_API_KEY_ENV: "k", AZURE_ENDPOINT_ENV: "https://corp.openai.azure.com"}

    target = resolve_llm_target(env)

    assert target.provider == "azure"
    assert target.base_url == "https://corp.openai.azure.com"


def test_azure_without_endpoint_is_rejected():
    with pytest.raises(InvalidLLMConfig):
        resolve_model_target("azure/gpt-4o", {AZURE_API_KEY_ENV: "k"})


def test_openai_gateway_base_url_is_honored():
    env = {"OPENAI_API_KEY": "k", "OPENAI_BASE_URL": "https://gateway.corp/v1"}

    target = resolve_llm_target(env)

    assert target.provider == "openai"
    assert target.base_url == "https://gateway.corp/v1"


def test_unsupported_provider_in_model_is_rejected():
    with pytest.raises(InvalidLLMConfig):
        resolve_model_target("cohere/command-r", {})


def test_resolve_model_target_ollama_uses_its_base_url_and_no_key():
    target = resolve_model_target("ollama/llama3.2", {OLLAMA_BASE_URL_ENV: "http://gpu:11434"})

    assert target.provider == "ollama"
    assert target.base_url == "http://gpu:11434"
    assert target.api_key_env is None


def test_resolve_model_target_openai_honors_the_gateway_base_url():
    target = resolve_model_target(
        "openai/gpt-4o", {"OPENAI_API_KEY": "k", "OPENAI_BASE_URL": "https://gw.corp/v1"}
    )

    assert target.base_url == "https://gw.corp/v1"


def test_resolve_model_target_without_a_slash_defaults_to_openai():
    target = resolve_model_target("gpt-4o", {"OPENAI_API_KEY": "k"})

    assert target.provider == "openai"


# --- segredo nunca no value object (métrica 3) -----------------------------


def test_target_never_carries_the_key_value():
    target = resolve_llm_target(ANTHROPIC)

    assert "sk-ant-xxx" not in repr(target)
    assert "sk-ant-xxx" not in str(target)
    assert target.api_key_env == "ANTHROPIC_API_KEY"


def test_ollama_target_requires_no_key():
    assert LLMTarget("ollama", "ollama/llama3.2", DEFAULT_OLLAMA_BASE_URL).requires_key is False


# --- disponibilidade e degradação (cenário 3, critério A5) -----------------


def test_available_providers_always_includes_ollama_last():
    candidates = available_providers({})

    assert candidates[-1].target.provider == "ollama"
    assert candidates[-1].needs_probe is True


def test_available_providers_lists_api_keys_first():
    candidates = available_providers(ANTHROPIC)

    assert candidates[0].target.provider == "anthropic"
    assert candidates[0].needs_probe is False


def test_onboarding_blocked_keeps_the_deterministic_floor():
    status = onboarding_status(semantic_ready=False)

    assert status.semantic_ready is False
    assert status.deterministic_ready is True
    assert status.gate_open is False
    # Orienta as DUAS vias (cenário 3).
    assert "ANTHROPIC_API_KEY" in status.guidance
    assert "OLLAMA_BASE_URL" in status.guidance


def test_onboarding_ready_opens_the_gate_without_noise():
    status = onboarding_status(semantic_ready=True)

    assert status.gate_open is True
    assert status.guidance == ""
