"""LiteLLM client behind the core `LLMClient` port (SPEC-005, ADR-005).

litellm lives here and nowhere else. Every method translates a litellm failure
into an `LLMError` via `classify`, so callers never see a provider exception and
never see an API key. The completion callable is injectable so the contract
tests run hermetically — no network, no key.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterator, Mapping
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel
from specharness_core.config import RoutingConfig
from specharness_core.ports.llm import (
    CompletionReport,
    LLMTarget,
    resolve_llm_target,
    resolve_model_target,
)

from .errors import classify

S = TypeVar("S", bound=BaseModel)

CompletionFn = Callable[..., Any]

#: SPEC-005, métrica 1: `llm test` valida em < 15s por provedor.
DEFAULT_TIMEOUT_S = 15.0

_PING_PROMPT = (
    "Isto é um teste de conectividade. Responda um JSON com o campo `ok` "
    "verdadeiro e uma mensagem curta em português no campo `message`."
)


class Ping(BaseModel):
    """The structured payload `llm test` asks the model to return (critério 2)."""

    ok: bool
    message: str


class LiteLlmClient:
    """Implements `LLMClient` over litellm."""

    def __init__(
        self,
        target: LLMTarget,
        env: Mapping[str, str],
        *,
        completion_fn: CompletionFn | None = None,
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> None:
        self._target = target
        self._completion: CompletionFn = completion_fn or litellm.completion
        self._timeout = timeout_s
        # The key is read here, at the edge, and only handed to litellm — it is
        # never stored on the target (SPEC-005, métrica 3).
        self._api_key = env.get(target.api_key_env) if target.api_key_env else None

    @property
    def target(self) -> LLMTarget:
        return self._target

    def _invoke(self, prompt: str, *, response_format: Any = None, stream: bool = False) -> Any:
        try:
            return self._completion(
                model=self._target.model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self._api_key,
                base_url=self._target.base_url,
                timeout=self._timeout,
                response_format=response_format,
                stream=stream,
            )
        except Exception as exc:
            raise classify(exc, self._target.provider, self._target.model) from exc

    def complete(self, prompt: str) -> str:
        return _text_of(self._invoke(prompt))

    def structured(self, prompt: str, schema: type[S]) -> S:
        response = self._invoke(prompt, response_format=schema)
        return schema.model_validate_json(_text_of(response))

    def stream(self, prompt: str) -> Iterator[str]:
        response = self._invoke(prompt, stream=True)
        for chunk in response:
            text = _chunk_text(chunk)
            if text:
                yield text

    def test(self) -> CompletionReport:
        """Real call with validated structured output + measured latency/cost.

        Latency is measured with `perf_counter` (ADR-016: medida, não afirmada);
        cost comes from litellm when it can price the model, else `None`.
        """
        started = time.perf_counter()
        response = self._invoke(_PING_PROMPT, response_format=Ping)
        elapsed = time.perf_counter() - started
        text = _text_of(response)
        Ping.model_validate_json(text)  # prove the structured output validates
        return CompletionReport(
            provider=self._target.provider,
            model=self._target.model,
            latency_s=elapsed,
            cost_usd=_safe_cost(response),
            output=text,
        )


def _text_of(response: Any) -> str:
    return response.choices[0].message.content


def _chunk_text(chunk: Any) -> str:
    delta = chunk.choices[0].delta
    return getattr(delta, "content", None) or ""


def _safe_cost(response: Any) -> float | None:
    """Best-effort cost in USD. Ollama and unpriced models report `None`."""
    hidden = getattr(response, "_hidden_params", None)
    if isinstance(hidden, dict) and hidden.get("response_cost") is not None:
        return float(hidden["response_cost"])
    try:
        return float(litellm.completion_cost(completion_response=response))
    except Exception:
        return None


def client_from_env(
    env: Mapping[str, str] | None = None,
    routing: RoutingConfig | None = None,
    task: str | None = None,
    *,
    completion_fn: CompletionFn | None = None,
) -> LiteLlmClient:
    """Build the client the CLI uses: resolve in the core, then reach litellm."""
    resolved = os.environ if env is None else env
    target = resolve_llm_target(resolved, routing=routing, task=task)
    return LiteLlmClient(target, resolved, completion_fn=completion_fn)


def check_connection(
    env: Mapping[str, str] | None = None,
    routing: RoutingConfig | None = None,
    task: str | None = None,
    *,
    completion_fn: CompletionFn | None = None,
) -> CompletionReport:
    """Test the primary target; on failure, fall back to the routed fallback.

    ADR-006 degradation with transparency: when the default model fails at
    runtime and `specharness.yaml` declares a `fallback`, the fallback is tried
    before giving up (SPEC-005, cenário de fallback).
    """
    resolved = os.environ if env is None else env
    try:
        return client_from_env(
            resolved, routing=routing, task=task, completion_fn=completion_fn
        ).test()
    except Exception:
        if routing is not None and routing.fallback:
            fallback_target = resolve_model_target(routing.fallback, resolved)
            return LiteLlmClient(fallback_target, resolved, completion_fn=completion_fn).test()
        raise
