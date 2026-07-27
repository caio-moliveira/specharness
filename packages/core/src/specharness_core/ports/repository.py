"""Repository port — connecting a GitHub repo to the onboarding (SPEC-006).

Pure domain (ADR-001): no git subprocess, no httpx, no network. What lives here
are the *shapes* and *decisions* — what a commit and a pull request are once
ingested, how a remote URL maps to an owner/repo, and what a failure is allowed
to say. ADR-011 fixes the source split: commit history comes from the local git
CLI (with `trailers.extract_spec_trailers` as the pure mirror), and the GitHub
API complements it with pull requests.

A token never lives in a value object here — only the *name* of the environment
variable that holds it — so nothing in this module can leak it (mesma garantia
da porta de LLM).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

#: The token is read from the environment, never from a config file.
GITHUB_TOKEN_ENV = "GITHUB_TOKEN"

#: Documented minimum scope (SPEC-006, critério de aceite / cenário 3). A
#: classic PAT needs `repo`; a fine-grained token needs read on Contents and
#: Pull requests.
MINIMAL_TOKEN_SCOPE = (
    "'repo' (PAT clássico) ou, em token fine-grained, leitura de Contents e Pull requests"
)

GITHUB_API_ROOT = "https://api.github.com"


class RepositoryError(Exception):
    """Base of every repository failure the user can act on."""

    template = "Falha ao acessar o repositório {repo}."

    @classmethod
    def for_repo(cls, repo: str, detail: str = "") -> RepositoryError:
        message = cls.template.format(
            repo=repo, token_env=GITHUB_TOKEN_ENV, scope=MINIMAL_TOKEN_SCOPE
        )
        return cls(f"{message} ({detail})" if detail else message)


class AuthenticationFailed(RepositoryError):
    template = (
        "Falha de autenticação no GitHub para {repo}. Verifique o token em {token_env} "
        "e garanta o escopo mínimo: {scope}."
    )


class RateLimited(RepositoryError):
    template = (
        "O GitHub recusou por limite de uso (rate limit) ao ler {repo}. "
        "Aguarde a janela de limite reabrir e rode o sync de novo."
    )


class RepositoryNotFound(RepositoryError):
    template = (
        "Repositório {repo} não encontrado no GitHub. Verifique o nome e se o token "
        "em {token_env} enxerga repositórios privados."
    )


class InvalidRepositoryConfig(RepositoryError):
    template = "Configuração de repositório inválida."

    @classmethod
    def because(cls, reason: str) -> InvalidRepositoryConfig:
        return cls(f"Configuração de repositório inválida: {reason}.")


@dataclass(frozen=True)
class RepoRef:
    """A GitHub repository coordinate."""

    owner: str
    name: str

    @property
    def slug(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class Commit:
    """A commit ingested from the local git history (SPEC-006, critério 2)."""

    sha: str
    author: str
    authored_at: datetime
    message: str
    spec_trailers: tuple[str, ...] = ()

    @property
    def subject(self) -> str:
        return self.message.strip().splitlines()[0] if self.message.strip() else ""


@dataclass(frozen=True)
class PullRequest:
    """A pull request ingested from the GitHub API (SPEC-006, critério 3)."""

    number: int
    title: str
    state: str
    head_branch: str
    base_branch: str
    commit_shas: tuple[str, ...] = ()


@dataclass(frozen=True)
class SyncResult:
    """Outcome of a repository sync (SPEC-006, métrica 2).

    A second run over an unchanged repo inserts nothing: `was_noop` is True.
    """

    new_commits: int
    new_pull_requests: int
    total_commits: int
    total_pull_requests: int

    @property
    def was_noop(self) -> bool:
        return self.new_commits == 0 and self.new_pull_requests == 0


@runtime_checkable
class CommitReader(Protocol):
    """What a commit source (the git CLI wrapper) must provide."""

    def commits(self) -> Iterator[Commit]: ...


@runtime_checkable
class PullRequestReader(Protocol):
    """What a pull-request source (the GitHub API client) must provide."""

    def pull_requests(self) -> Iterator[PullRequest]: ...


@runtime_checkable
class RepositoryStore(Protocol):
    """Where ingested commits and pull requests are persisted, idempotently."""

    def sync(
        self, repo: str, commits: list[Commit], pull_requests: list[PullRequest]
    ) -> SyncResult: ...


# --- pure parsing ----------------------------------------------------------

_REMOTE_RES = (
    re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<name>.+?)(?:\.git)?$"),
    re.compile(
        r"^(?:https?|ssh)://(?:[^@]+@)?github\.com/(?P<owner>[^/]+)/(?P<name>.+?)(?:\.git)?$"
    ),
)


def parse_github_remote(url: str) -> RepoRef:
    """Map a git remote URL to a `RepoRef`, or raise `InvalidRepositoryConfig`.

    Handles the three forms git hands out: `git@github.com:owner/repo.git`,
    `https://github.com/owner/repo(.git)` and `ssh://git@github.com/owner/repo`.
    """
    candidate = url.strip()
    for pattern in _REMOTE_RES:
        match = pattern.match(candidate)
        if match:
            name = match.group("name").removesuffix(".git")
            return RepoRef(owner=match.group("owner"), name=name)
    raise InvalidRepositoryConfig.because(f"não reconheço a URL de remote do GitHub: {candidate!r}")
