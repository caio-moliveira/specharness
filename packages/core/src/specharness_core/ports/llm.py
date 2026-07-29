"""LLM port — the mandatory onboarding connection (SPEC-005).

Pure domain (ADR-001): no litellm, no httpx, no network. What lives here are
*decisions* — which provider we resolve to from the environment, which model a
task routes to, and what a failure is allowed to say. ADR-006 makes the LLM
mandatory: the onboarding needs one working path (a provider API or local
Ollama) before the Readiness Gate opens, and the deterministic floor runs
regardless — in a runtime failure the semantic layer is left *explicitly*
pending, never silently skipped.

ADR-005 fixes the contract: the core speaks only to `LLMClient` (complete,
structured, stream); litellm lives behind it in an adapter.

A resolved `LLMTarget` never carries the secret itself — only the *name* of the
environment variable that holds it. No value object here can leak a key, which
is what lets SPEC-005 promise "0 keys em arquivos de config" (métrica 3).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

#: Provider credentials — read from the environment, never from a config file
#: (SPEC-005, métrica 3; `.env.example` spells the contract out).
ANTHROPIC_API_KEY_ENV = "ANTHROPIC_API_KEY"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
AZURE_API_KEY_ENV = "AZURE_OPENAI_API_KEY"
AZURE_ENDPOINT_ENV = "AZURE_OPENAI_ENDPOINT"
#: O roteamento azure do litellm EXIGE a api_version; sem ela a conexão falha
#: (SPEC-027). Como base_url/api_key, é lida do ambiente, nunca de config.
AZURE_API_VERSION_ENV = "AZURE_OPENAI_API_VERSION"
OPENAI_BASE_URL_ENV = "OPENAI_BASE_URL"
OLLAMA_BASE_URL_ENV = "OLLAMA_BASE_URL"

#: Ollama's zero-cost path answers here by default; the user only sets the var
#: to point elsewhere (SPEC-005, cenário "custo zero").
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"

#: The product's default model per provider — the zero-config fallback. A
#: project overrides these per task in `specharness.yaml` (see `config.py`).
DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "anthropic/claude-sonnet-4-6",
    "openai": "openai/gpt-4o-mini",
    "azure": "azure/gpt-4o-mini",
    "ollama": "ollama/llama3.2",
}

S = TypeVar("S", bound=BaseModel)


class LLMError(Exception):
    """Base of every LLM failure the user can act on.

    The message names the provider and the knob to turn; the underlying
    provider text is never echoed (it can carry the request payload, API key
    and all — SPEC-005, métrica 3).
    """

    template = "Falha na conexão LLM com {provider}."

    @classmethod
    def for_provider(cls, provider: str, detail: str = "") -> LLMError:
        message = cls.template.format(provider=provider)
        return cls(f"{message} ({detail})" if detail else message)


class AuthenticationFailed(LLMError):
    template = (
        "Falha de autenticação no provedor {provider}. "
        "Verifique a API key na variável de ambiente do provedor."
    )


class RateLimited(LLMError):
    template = (
        "O provedor {provider} recusou por limite de uso (rate limit). "
        "Tente novamente em instantes ou reduza a frequência."
    )


class Timeout(LLMError):
    template = "O provedor {provider} não respondeu a tempo. Verifique a rede e tente de novo."


class ProviderUnreachable(LLMError):
    template = (
        "Não foi possível alcançar o provedor {provider}. "
        "Verifique a rede, a base_url e se o serviço está no ar."
    )


class NoProviderConfigured(LLMError):
    """No LLM path at all — the onboarding is blocked (SPEC-005, cenário 3)."""

    template = (
        "Nenhuma via de LLM disponível. Defina uma API key "
        f"({ANTHROPIC_API_KEY_ENV}, {OPENAI_API_KEY_ENV} ou {AZURE_API_KEY_ENV}) "
        f"ou suba o Ollama local e aponte {OLLAMA_BASE_URL_ENV}. Uma via funcional é "
        "obrigatória para liberar o Readiness Gate (ADR-006)."
    )

    @classmethod
    def guidance(cls) -> NoProviderConfigured:
        return cls(cls.template)

    @classmethod
    def for_missing_key(cls, provider: str, env_var: str) -> NoProviderConfigured:
        return cls(
            f"O provedor {provider} está no roteamento, mas {env_var} não está "
            f"definida. Defina-a ou ajuste o modelo em specharness.yaml."
        )


class InvalidLLMConfig(LLMError):
    template = "Configuração de LLM inválida."

    @classmethod
    def because(cls, reason: str) -> InvalidLLMConfig:
        return cls(f"Configuração de LLM inválida: {reason}.")


@dataclass(frozen=True)
class LLMTarget:
    """A resolved LLM provider target.

    Carries the *name* of the credential env var, never the secret — so the
    target can be logged, repr'd and shown without leaking a key.
    """

    provider: str
    model: str
    base_url: str | None = None
    api_key_env: str | None = None
    api_version: str | None = None  # azure exige; não é segredo (SPEC-027)

    @property
    def requires_key(self) -> bool:
        return self.api_key_env is not None


@dataclass(frozen=True)
class ProviderCandidate:
    """A provider that *might* serve, pending liveness.

    `needs_probe` is True only for Ollama: an API key is a candidate on sight,
    but a local server has to answer before we offer it (SPEC-005, cenário 2).
    """

    target: LLMTarget
    needs_probe: bool


@dataclass(frozen=True)
class CompletionReport:
    """What `llm test` reports back (SPEC-005, critério 2)."""

    provider: str
    model: str
    latency_s: float
    cost_usd: float | None
    output: str

    @property
    def cost_label(self) -> str:
        return "n/d" if self.cost_usd is None else f"US$ {self.cost_usd:.6f}"


@dataclass(frozen=True)
class OnboardingLLMStatus:
    """Whether the LLM gate may open, and what still runs if it may not.

    ADR-006: the deterministic floor is always available; only the semantic
    layer waits on a working LLM. A runtime failure degrades to
    `semantic_ready=False` *with* guidance — transparently, never silently.
    """

    semantic_ready: bool
    deterministic_ready: bool
    guidance: str

    @property
    def gate_open(self) -> bool:
        return self.semantic_ready


@runtime_checkable
class LLMClient(Protocol):
    """What an adapter must provide (ADR-005 names these three verbs)."""

    @property
    def target(self) -> LLMTarget: ...

    def complete(self, prompt: str) -> str:
        """A plain completion, or raise an `LLMError`."""
        ...

    def structured(self, prompt: str, schema: type[S]) -> S:
        """A completion validated against a Pydantic schema (SPEC-005, critério 2)."""
        ...

    def stream(self, prompt: str) -> Iterator[str]:
        """Stream text chunks, or raise an `LLMError`."""
        ...


# --- resolution (pure) -----------------------------------------------------


def _has(env: Mapping[str, str], key: str) -> bool:
    return bool(env.get(key, "").strip())


def _api_providers(env: Mapping[str, str]) -> list[ProviderCandidate]:
    """API-key providers present in the environment, in precedence order."""
    out: list[ProviderCandidate] = []
    if _has(env, ANTHROPIC_API_KEY_ENV):
        out.append(
            ProviderCandidate(
                LLMTarget("anthropic", DEFAULT_MODELS["anthropic"], None, ANTHROPIC_API_KEY_ENV),
                needs_probe=False,
            )
        )
    if _has(env, OPENAI_API_KEY_ENV):
        base = env.get(OPENAI_BASE_URL_ENV, "").strip() or None
        out.append(
            ProviderCandidate(
                LLMTarget("openai", DEFAULT_MODELS["openai"], base, OPENAI_API_KEY_ENV),
                needs_probe=False,
            )
        )
    if _has(env, AZURE_API_KEY_ENV):
        endpoint = env.get(AZURE_ENDPOINT_ENV, "").strip() or None
        api_version = env.get(AZURE_API_VERSION_ENV, "").strip() or None
        out.append(
            ProviderCandidate(
                LLMTarget(
                    "azure", DEFAULT_MODELS["azure"], endpoint, AZURE_API_KEY_ENV, api_version
                ),
                needs_probe=False,
            )
        )
    return out


def _ollama_candidate(env: Mapping[str, str]) -> ProviderCandidate:
    """Ollama at the configured base_url, or the default localhost endpoint.

    Always a candidate (liveness is the adapter's call): the zero-cost path is
    offered whenever a local server happens to answer, even with the var unset.
    """
    base = env.get(OLLAMA_BASE_URL_ENV, "").strip() or DEFAULT_OLLAMA_BASE_URL
    return ProviderCandidate(
        LLMTarget("ollama", DEFAULT_MODELS["ollama"], base, None), needs_probe=True
    )


def available_providers(env: Mapping[str, str]) -> tuple[ProviderCandidate, ...]:
    """Every candidate the environment allows: API keys first, then Ollama."""
    return (*_api_providers(env), _ollama_candidate(env))


def resolve_model_target(model: str, env: Mapping[str, str]) -> LLMTarget:
    """Resolve the credentials/base_url for an explicit model string.

    The provider is the litellm prefix (`anthropic/…`, `azure/…`); the required
    env var must be present, or the resolution raises with the exact knob.
    """
    provider = model.split("/", 1)[0] if "/" in model else "openai"
    if provider == "anthropic":
        if not _has(env, ANTHROPIC_API_KEY_ENV):
            raise NoProviderConfigured.for_missing_key(provider, ANTHROPIC_API_KEY_ENV)
        return LLMTarget("anthropic", model, None, ANTHROPIC_API_KEY_ENV)
    if provider == "openai":
        if not _has(env, OPENAI_API_KEY_ENV):
            raise NoProviderConfigured.for_missing_key(provider, OPENAI_API_KEY_ENV)
        base = env.get(OPENAI_BASE_URL_ENV, "").strip() or None
        return LLMTarget("openai", model, base, OPENAI_API_KEY_ENV)
    if provider == "azure":
        if not _has(env, AZURE_API_KEY_ENV):
            raise NoProviderConfigured.for_missing_key(provider, AZURE_API_KEY_ENV)
        endpoint = env.get(AZURE_ENDPOINT_ENV, "").strip() or None
        if endpoint is None:
            raise InvalidLLMConfig.because(f"o provedor azure exige {AZURE_ENDPOINT_ENV}")
        api_version = env.get(AZURE_API_VERSION_ENV, "").strip() or None
        if api_version is None:
            raise InvalidLLMConfig.because(f"o provedor azure exige {AZURE_API_VERSION_ENV}")
        return LLMTarget("azure", model, endpoint, AZURE_API_KEY_ENV, api_version)
    if provider == "ollama":
        base = env.get(OLLAMA_BASE_URL_ENV, "").strip() or DEFAULT_OLLAMA_BASE_URL
        return LLMTarget("ollama", model, base, None)
    raise InvalidLLMConfig.because(f"provedor '{provider}' no modelo '{model}' não é suportado")


def resolve_llm_target(
    env: Mapping[str, str],
    routing: RoutingConfigLike | None = None,
    task: str | None = None,
) -> LLMTarget:
    """Resolve which provider/model the onboarding should use.

    With routing, the model comes from the task (or the default) and its
    credentials are looked up. Without routing, the first API provider present
    wins; failing that, Ollama is the target to attempt — its liveness is the
    adapter's to prove (SPEC-005, cenários 1 e 2).
    """
    if routing is not None:
        model = routing.model_for_task(task) if task is not None else routing.default
        return resolve_model_target(model, env)
    apis = _api_providers(env)
    if apis:
        return apis[0].target
    return _ollama_candidate(env).target


def onboarding_status(*, semantic_ready: bool) -> OnboardingLLMStatus:
    """Compose the gate status. The deterministic floor is always available."""
    guidance = "" if semantic_ready else NoProviderConfigured.template
    return OnboardingLLMStatus(
        semantic_ready=semantic_ready, deterministic_ready=True, guidance=guidance
    )


class RoutingConfigLike(Protocol):
    """The slice of routing config the resolver needs (defined in `config.py`)."""

    @property
    def default(self) -> str: ...

    def model_for_task(self, task: str) -> str: ...
