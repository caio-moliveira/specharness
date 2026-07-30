"""Step definitions da SPEC-029 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-029 --steps specs/steps/spec_029_steps.py`.
Os passos rodam o `track` de verdade via CliRunner, com o store de commits e o
registro de specs substituídos em memória — mesmo padrão hermético dos testes
de CLI (packages/cli/tests/test_track.py), sem banco e sem rede.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_cli import main
from specharness_core import SpecInfo
from specharness_core.ports.repository import Commit
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {"commits": [], "specs": [], "output": ""}


class _FakeGateway:
    target = None

    def migrate(self) -> None:
        pass


def _run_track() -> str:
    """Roda `specharness track` com os dados do cenário, restaurando tudo ao final."""
    originals = (main.gateway_from_env, main.RepositoryStore, main._load_spec_infos)
    commits = list(_state["commits"])

    class _FakeStore:
        def __init__(self, target: Any) -> None:
            pass

        def all_commits(self) -> list[Commit]:
            return commits

    main.gateway_from_env = lambda: _FakeGateway()
    main.RepositoryStore = _FakeStore
    main._load_spec_infos = lambda: list(_state["specs"])
    try:
        return CliRunner().invoke(main.app, ["track"]).output
    finally:
        main.gateway_from_env, main.RepositoryStore, main._load_spec_infos = originals


@registry.step(r"um banco sem nenhum commit ingerido")
def _given_no_ingested_commits() -> None:
    _state["commits"] = []
    _state["specs"] = []


@registry.step(r"commits ingeridos todos com trailer de spec válido")
def _given_linked_commits() -> None:
    _state["commits"] = [
        Commit(
            sha="a" * 40,
            author="Ana",
            authored_at=datetime(2026, 7, 30),
            message="feat: x",
            spec_trailers=("SPEC-029",),
        )
    ]
    _state["specs"] = [SpecInfo("SPEC-029", "in_progress", "2026-C2")]


@registry.step(r"o track roda")
def _when_track_runs() -> None:
    _state["output"] = _run_track()


@registry.step(r"a saída informa que nenhum commit foi ingerido e orienta")
def _then_guides_to_ingestion() -> None:
    assert "Nenhum commit ingerido" in _state["output"], _state["output"]
    assert "specharness connect repo" in _state["output"], _state["output"]


@registry.step(r"a saída não contém \"✓ Pipeline limpa\"")
def _then_not_reported_clean() -> None:
    assert "✓ Pipeline limpa" not in _state["output"], _state["output"]


@registry.step(r"a saída contém \"✓ Pipeline limpa\"")
def _then_reported_clean() -> None:
    assert "✓ Pipeline limpa" in _state["output"], _state["output"]
