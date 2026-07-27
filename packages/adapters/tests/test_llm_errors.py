"""litellm exceptions become actionable, secret-free LLMErrors (SPEC-005, A5)."""

from __future__ import annotations

import litellm
import pytest
from specharness_adapters.llm import LiteLlmClient, classify
from specharness_core.ports.llm import (
    AuthenticationFailed,
    LLMError,
    ProviderUnreachable,
    RateLimited,
    Timeout,
)

MODEL = "anthropic/claude-3-5-sonnet-latest"


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (
            litellm.AuthenticationError(message="bad", llm_provider="anthropic", model=MODEL),
            AuthenticationFailed,
        ),
        (
            litellm.RateLimitError(message="slow", llm_provider="anthropic", model=MODEL),
            RateLimited,
        ),
        (litellm.Timeout(message="late", model=MODEL, llm_provider="anthropic"), Timeout),
        (
            litellm.APIConnectionError(message="down", llm_provider="anthropic", model=MODEL),
            ProviderUnreachable,
        ),
        (
            litellm.ServiceUnavailableError(message="503", llm_provider="anthropic", model=MODEL),
            ProviderUnreachable,
        ),
    ],
)
def test_each_litellm_error_maps_to_its_core_error(exc, expected):
    result = classify(exc, "anthropic", MODEL)

    assert isinstance(result, expected)
    assert result.__cause__ is exc


def test_unknown_exception_falls_back_to_the_base_error():
    result = classify(ValueError("algo estranho"), "openai", MODEL)

    assert isinstance(result, LLMError)
    assert type(result) is LLMError


def test_the_message_never_echoes_the_driver_text():
    """A litellm pode incluir o payload (com a key) no texto — nunca o repassamos."""
    leaky = litellm.AuthenticationError(
        message="auth failed for api_key=sk-super-secret-xyz",
        llm_provider="anthropic",
        model=MODEL,
    )

    result = classify(leaky, "anthropic", MODEL)

    assert "sk-super-secret-xyz" not in str(result)
    assert "anthropic" in str(result).lower()


def test_a_client_call_surfaces_the_classified_error_not_the_raw_one():
    def boom(*, model, messages, response_format=None, stream=False, **kwargs):
        raise litellm.AuthenticationError(
            message="key=sk-leak", llm_provider="anthropic", model=model
        )

    from specharness_core.ports.llm import LLMTarget

    client = LiteLlmClient(
        LLMTarget("anthropic", MODEL, None, "ANTHROPIC_API_KEY"),
        {"ANTHROPIC_API_KEY": "sk-leak"},
        completion_fn=boom,
    )

    with pytest.raises(AuthenticationFailed) as excinfo:
        client.complete("oi")

    assert "sk-leak" not in str(excinfo.value)
