"""Onboarding: o que o `specharness init` grava, como lógica pura (SPEC-022).

Sem I/O e sem framework (ADR-001): dadas as seleções do time, produz o texto do
`specharness.yaml` (só não-segredo) e a lista de nomes de env var das credenciais
que o `.env` precisa. Prompts, escrita de arquivo e `.gitignore` são do CLI.

A garantia central (ADR-006, métrica 4): nenhum VALOR de credencial passa por
aqui — só o NOME da variável de ambiente que a guarda.
"""

from __future__ import annotations

from dataclasses import dataclass

from .ports.database import DATABASE_URL_ENV
from .ports.llm import (
    ANTHROPIC_API_KEY_ENV,
    AZURE_API_KEY_ENV,
    AZURE_API_VERSION_ENV,
    AZURE_ENDPOINT_ENV,
    DEFAULT_MODELS,
    OLLAMA_BASE_URL_ENV,
    OPENAI_API_KEY_ENV,
)
from .ports.repository import GITHUB_TOKEN_ENV
from .ports.tracker import (
    JIRA_EMAIL_ENV,
    JIRA_TOKEN_ENV,
    JIRA_URL_ENV,
    REDMINE_API_KEY_ENV,
)

#: A URL do Redmine é do ambiente (como no .env.example), mas não tem constante
#: própria numa porta — é do adapter. Declarada aqui para o scaffold do .env.
REDMINE_URL_ENV = "REDMINE_URL"

#: Categorias que o init pergunta, na ordem dos prompts.
CATEGORIES = ("tracker", "git", "db", "agent", "llm")

#: Opções válidas por categoria (a primeira é o default sugerido).
OPTIONS: dict[str, tuple[str, ...]] = {
    "tracker": ("github-issues", "redmine", "jira", "none"),
    "git": ("github", "none"),
    "db": ("sqlite", "postgres"),
    "agent": ("claude-code", "codex", "kimi"),
    "llm": ("anthropic", "openai", "azure", "ollama"),
}

#: Nomes de env var (SÓ segredos/conexão) que cada opção exige no .env.
SECRET_ENV: dict[tuple[str, str], tuple[str, ...]] = {
    ("tracker", "github-issues"): (GITHUB_TOKEN_ENV,),
    ("tracker", "redmine"): (REDMINE_URL_ENV, REDMINE_API_KEY_ENV),
    ("tracker", "jira"): (JIRA_URL_ENV, JIRA_EMAIL_ENV, JIRA_TOKEN_ENV),
    ("tracker", "none"): (),
    ("git", "github"): (GITHUB_TOKEN_ENV,),
    ("git", "none"): (),
    ("db", "sqlite"): (),
    ("db", "postgres"): (DATABASE_URL_ENV,),
    ("agent", "claude-code"): (),
    ("agent", "codex"): (),
    ("agent", "kimi"): (),
    ("llm", "anthropic"): (ANTHROPIC_API_KEY_ENV,),
    ("llm", "openai"): (OPENAI_API_KEY_ENV,),
    ("llm", "azure"): (AZURE_API_KEY_ENV, AZURE_ENDPOINT_ENV, AZURE_API_VERSION_ENV),
    ("llm", "ollama"): (OLLAMA_BASE_URL_ENV,),
}


class InvalidSelection(ValueError):
    """Uma seleção fora do catálogo — erro do usuário, acionável."""


@dataclass(frozen=True)
class Selections:
    """As escolhas do time no init. Uma opção por categoria."""

    tracker: str
    git: str
    db: str
    agent: str
    llm: str

    def as_map(self) -> dict[str, str]:
        return {
            "tracker": self.tracker,
            "git": self.git,
            "db": self.db,
            "agent": self.agent,
            "llm": self.llm,
        }

    def __post_init__(self) -> None:
        for category, value in self.as_map().items():
            if value not in OPTIONS[category]:
                allowed = ", ".join(OPTIONS[category])
                raise InvalidSelection(f"'{value}' inválido para {category}; use um de: {allowed}")


def env_vars_for(selections: Selections) -> list[str]:
    """Nomes de env var que o .env precisa, sem duplicar, em ordem estável."""
    chosen = selections.as_map()
    ordered: list[str] = []
    for category in CATEGORIES:
        for name in SECRET_ENV[(category, chosen[category])]:
            if name not in ordered:
                ordered.append(name)
    return ordered


def render_config(selections: Selections) -> str:
    """O texto do specharness.yaml (só não-segredo), determinístico e idempotente."""
    chosen = selections.as_map()
    lines = [
        "# specharness.yaml — gerado por `specharness init` (SPEC-022).",
        "# Credenciais NUNCA aqui — só no .env (ADR-006). Ajuste o modelo se preciso.",
        "init:",
    ]
    for category in CATEGORIES:
        lines.append(f"  {category}: {chosen[category]}")
    lines += [
        "llm:",
        # Fonte única: o mesmo default do runtime (ports/llm), sem divergir (SPEC-027).
        f"  default: {DEFAULT_MODELS[selections.llm]}",
        "",
    ]
    return "\n".join(lines)
