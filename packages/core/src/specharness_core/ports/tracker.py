"""Tracker port — importing issues as canonical WorkItems (SPEC-007, ADR-007).

Pure domain (ADR-001): no httpx, no Redmine types. The core knows only the
`WorkItem` — id, tipo, título, estado, sprint, origem, ref externa, extras — and
adapters translate each tracker's taxonomy into it, in both directions. Fields
without a canonical home go to `extras`, never discarded (ADR-007, critério 3).

The API key never lives in a value object here — only the *name* of the env var
that holds it (mesma garantia das portas de LLM e repositório).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

#: The Redmine API key is read from the environment, never from a config file.
REDMINE_API_KEY_ENV = "REDMINE_API_KEY"


class TrackerError(Exception):
    """Base of every tracker failure the user can act on."""

    template = "Falha ao acessar o tracker {tracker}."

    @classmethod
    def for_tracker(cls, tracker: str, detail: str = "") -> TrackerError:
        message = cls.template.format(tracker=tracker, key_env=REDMINE_API_KEY_ENV)
        return cls(f"{message} ({detail})" if detail else message)


class TrackerAuthenticationFailed(TrackerError):
    template = "Falha de autenticação no tracker {tracker}. Verifique a API key em {key_env}."


class TrackerRateLimited(TrackerError):
    template = (
        "O tracker {tracker} recusou por limite de uso (rate limit). "
        "Aguarde a janela reabrir e rode o import de novo."
    )


class TrackerNotFound(TrackerError):
    template = (
        "Recurso não encontrado no tracker {tracker}. Verifique a URL e o projeto configurados."
    )


class InvalidTrackerConfig(TrackerError):
    template = "Configuração de tracker inválida."

    @classmethod
    def because(cls, reason: str) -> InvalidTrackerConfig:
        return cls(f"Configuração de tracker inválida: {reason}.")


@dataclass(frozen=True)
class WorkItem:
    """The canonical work item (ADR-007). One shape for every tracker."""

    origin: str  # qual tracker: "redmine"
    external_id: str  # id estável no tracker
    kind: str  # tipo canônico: "issue" | "version"
    title: str
    state: str  # estado — nome nativo do status (fidelidade, sem inventar)
    sprint: str | None = None
    url: str | None = None  # ref externa navegável
    extras: Mapping[str, Any] = field(default_factory=dict)

    @property
    def ref(self) -> str:
        """A stable external reference, unchanged across syncs (critério 1)."""
        return f"{self.origin}:{self.kind}:{self.external_id}"


@dataclass(frozen=True)
class ImportResult:
    """Outcome of an import/sync (SPEC-007, métricas 2 e 3).

    A re-import of unchanged items neither inserts nor updates: `was_noop`.
    """

    new_items: int
    updated_items: int
    total_items: int

    @property
    def was_noop(self) -> bool:
        return self.new_items == 0 and self.updated_items == 0


@runtime_checkable
class WorkItemReader(Protocol):
    """What a tracker importer must provide."""

    def work_items(self) -> Iterator[WorkItem]: ...


@runtime_checkable
class StatusWriter(Protocol):
    """The write-back capability: push a status to the tracker (critério 2)."""

    def update_status(self, external_id: str, status_name: str) -> None: ...


@runtime_checkable
class WorkItemStore(Protocol):
    """Where imported WorkItems are persisted, idempotently and with updates."""

    def sync(self, origin: str, items: list[WorkItem]) -> ImportResult: ...


def target_status(status_map: Mapping[str, str], spec_status: str) -> str:
    """The Redmine status name a spec status writes back to (pure, critério 2).

    The mapping is configured per instance (`tracker.status_map`), because each
    Redmine has its own workflow. An unmapped status is a config error, not a
    silent guess.
    """
    try:
        return status_map[spec_status]
    except KeyError:
        raise InvalidTrackerConfig.because(
            f"sem mapeamento de status para '{spec_status}' em tracker.status_map"
        ) from None
