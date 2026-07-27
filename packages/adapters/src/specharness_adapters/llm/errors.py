"""LiteLLM failure -> actionable `LLMError` (SPEC-005, critério 5 / A5).

The user never reads a litellm traceback. The provider's own text is never
echoed — it can carry the request payload, and an API key with it. Only the
exception class name, provider and model reach the message (mesma regra do
adapter de banco: `type(cause).__name__`, nunca `str(cause)`).
"""

from __future__ import annotations

import litellm
from specharness_core.ports.llm import (
    AuthenticationFailed,
    LLMError,
    ProviderUnreachable,
    RateLimited,
    Timeout,
)

#: litellm exception -> core error. Ordered: the first isinstance match wins, so
#: the specific auth/rate/timeout cases precede the broad connection ones.
_TYPE_MAP: tuple[tuple[tuple[type[BaseException], ...], type[LLMError]], ...] = (
    ((litellm.AuthenticationError,), AuthenticationFailed),
    ((litellm.RateLimitError,), RateLimited),
    ((litellm.Timeout,), Timeout),
    (
        (
            litellm.APIConnectionError,
            litellm.ServiceUnavailableError,
            litellm.InternalServerError,
            litellm.NotFoundError,
        ),
        ProviderUnreachable,
    ),
)


def classify(exc: BaseException, provider: str, model: str) -> LLMError:
    """Turn a litellm exception into an actionable `LLMError`.

    Never echoes `str(exc)`: a provider is free to include the request (API key
    included) in what it raises (SPEC-005, métrica 3).
    """
    for types, error_cls in _TYPE_MAP:
        if isinstance(exc, types):
            return _build(error_cls, provider, model, exc)
    return _build(LLMError, provider, model, exc)


def _build(error_cls: type[LLMError], provider: str, model: str, cause: BaseException) -> LLMError:
    error = error_cls.for_provider(provider, detail=f"{type(cause).__name__} [{model}]")
    error.__cause__ = cause
    return error
