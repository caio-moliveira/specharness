"""Provider detection (SPEC-005, cenário 2 / critério A1, métrica 2).

An API key is a candidate on sight — whether it actually works is proven by
`llm test`. Ollama is the only path we can probe cheaply: a GET to its
`/api/tags` in under 2s (métrica 2) says a local server is up, so the zero-cost
path can be offered as primary when there is no key.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

import httpx
from specharness_core.ports.llm import (
    DEFAULT_OLLAMA_BASE_URL,
    ProviderCandidate,
    available_providers,
)

#: SPEC-005, métrica 2: detecção do Ollama local em < 2s.
OLLAMA_PROBE_TIMEOUT_S = 2.0

ProbeFn = Callable[[str], bool]


def ollama_responds(base_url: str, *, timeout: float = OLLAMA_PROBE_TIMEOUT_S) -> bool:
    """Whether an Ollama server answers at `base_url` within the budget."""
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def detect_providers(
    env: Mapping[str, str], *, probe: ProbeFn | None = None
) -> list[ProviderCandidate]:
    """The candidates that are actually usable right now.

    API providers pass through (their key is present); the Ollama candidate is
    kept only if the probe confirms a live server. Order is preserved, so the
    first entry is the primary the onboarding should offer.
    """
    check = probe or ollama_responds
    live: list[ProviderCandidate] = []
    for candidate in available_providers(env):
        if not candidate.needs_probe:
            live.append(candidate)
            continue
        base = candidate.target.base_url or DEFAULT_OLLAMA_BASE_URL
        if check(base):
            live.append(candidate)
    return live
