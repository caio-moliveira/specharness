"""Provider detection (SPEC-005, cenário 2 e 3, critério A1).

The Ollama probe is injected, so these assertions never touch the network.
"""

from __future__ import annotations

from types import SimpleNamespace

import httpx
from specharness_adapters.llm import detect_providers, ollama_responds

ALIVE = lambda base_url: True  # noqa: E731 - a one-line probe stub reads clearer inline
DEAD = lambda base_url: False  # noqa: E731


class _FakeClient:
    """A stand-in for httpx.Client that answers with a fixed status or raises."""

    def __init__(self, *, status=200, boom=False):
        self._status = status
        self._boom = boom
        self.requested: list[str] = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url):
        if self._boom:
            raise httpx.ConnectError("recusada")
        self.requested.append(url)
        return SimpleNamespace(status_code=self._status)


# --- cenário 2: sem key, Ollama vivo é a via principal ---------------------


def test_ollama_is_offered_as_primary_when_no_key_and_it_responds():
    live = detect_providers({}, probe=ALIVE)

    assert live
    assert live[0].target.provider == "ollama"


def test_probe_receives_the_configured_base_url():
    seen: list[str] = []

    def spy(base_url: str) -> bool:
        seen.append(base_url)
        return True

    detect_providers({"OLLAMA_BASE_URL": "http://gpu-box:11434"}, probe=spy)

    assert seen == ["http://gpu-box:11434"]


# --- cenário 3: sem key e sem Ollama, nenhuma via --------------------------


def test_no_provider_is_live_when_no_key_and_ollama_is_down():
    assert detect_providers({}, probe=DEAD) == []


# --- cenário 1: uma API key é via principal sobre o Ollama -----------------


def test_an_api_key_is_primary_over_ollama():
    live = detect_providers({"ANTHROPIC_API_KEY": "x"}, probe=ALIVE)

    assert live[0].target.provider == "anthropic"


def test_an_api_key_alone_needs_no_probe():
    # DEAD would drop Ollama, but the API key stands on its own.
    live = detect_providers({"OPENAI_API_KEY": "x"}, probe=DEAD)

    assert [c.target.provider for c in live] == ["openai"]


# --- o probe real do Ollama (httpx sob mock) -------------------------------


def test_ollama_responds_is_true_on_http_200(monkeypatch):
    client = _FakeClient(status=200)
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: client)

    assert ollama_responds("http://localhost:11434/") is True
    assert client.requested == ["http://localhost:11434/api/tags"]


def test_ollama_responds_is_false_on_non_200(monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeClient(status=500))

    assert ollama_responds("http://localhost:11434") is False


def test_ollama_responds_is_false_when_the_connection_fails(monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda **kwargs: _FakeClient(boom=True))

    assert ollama_responds("http://localhost:11434") is False
