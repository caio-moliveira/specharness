"""Step definitions da SPEC-009 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-009 --steps specs/steps/spec_009_steps.py`.
Exercita o motor do track (`link_commits`, core puro) com commits e registro
de specs construídos em memória — o mesmo dado que a ingestão (SPEC-006)
entregaria, sem banco e sem rede.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_core import SpecInfo, link_commits
from specharness_core.ports.repository import Commit

registry = StepRegistry()

_state: dict[str, Any] = {}


def _commit(sha: str, trailers: tuple[str, ...]) -> Commit:
    return Commit(
        sha=sha,
        author="Ana",
        authored_at=datetime(2026, 7, 30),
        message="feat: x",
        spec_trailers=trailers,
    )


@registry.step(r"um commit cuja mensagem termina com o trailer \"Spec: SPEC-042\"")
def _given_commit_with_valid_trailer() -> None:
    _state["commits"] = [_commit("a" * 40, ("SPEC-042",))]
    _state["specs"] = [SpecInfo("SPEC-042", "in_progress", "2026-C2")]


@registry.step(r"um commit com trailer \"Spec: SPEC-999\" e nenhuma spec com esse id")
def _given_commit_with_unknown_spec() -> None:
    _state["commits"] = [_commit("b" * 40, ("SPEC-999",))]
    _state["specs"] = [SpecInfo("SPEC-042", "in_progress", "2026-C2")]


@registry.step(r"um commit sem nenhum trailer \"Spec:\"")
def _given_commit_without_trailer() -> None:
    _state["commits"] = [_commit("c" * 40, ())]
    _state["specs"] = []


@registry.step(r"uma spec in_progress sem nenhum commit vinculado")
def _given_orphan_spec() -> None:
    _state["commits"] = []
    _state["specs"] = [SpecInfo("SPEC-042", "in_progress", "2026-C2")]


@registry.step(r"um commit com trailers \"Spec: SPEC-010\" e \"Spec: SPEC-011\"")
def _given_commit_with_two_trailers() -> None:
    _state["commits"] = [_commit("d" * 40, ("SPEC-010", "SPEC-011"))]
    _state["specs"] = [
        SpecInfo("SPEC-010", "in_progress", "2026-C2"),
        SpecInfo("SPEC-011", "in_progress", "2026-C2"),
    ]


@registry.step(r"o track (processa o commit|é executado)")
def _when_track_links() -> None:
    _state["result"] = link_commits(_state["commits"], _state["specs"])


@registry.step(r"o commit fica vinculado à SPEC-042 na visão pipeline")
def _then_linked_to_spec_042() -> None:
    links = {(link.commit_sha, link.spec_id) for link in _state["result"].valid_links}
    assert ("a" * 40, "SPEC-042") in links, links


@registry.step(r"o commit é marcado com vínculo inválido e aparece no relatório de higiene")
def _then_flagged_invalid() -> None:
    result = _state["result"]
    invalid = {(link.commit_sha, link.spec_id) for link in result.invalid_links}
    assert ("b" * 40, "SPEC-999") in invalid, invalid
    assert not result.valid_links
    assert not result.is_clean


@registry.step(r"o commit entra na contagem de commits órfãos da sprint")
def _then_counted_as_orphan_commit() -> None:
    assert "c" * 40 in _state["result"].orphan_commits


@registry.step(r"a spec entra na contagem de specs órfãs")
def _then_counted_as_orphan_spec() -> None:
    assert "SPEC-042" in _state["result"].orphan_specs


@registry.step(r"o commit fica vinculado às duas specs")
def _then_linked_to_both() -> None:
    links = {(link.commit_sha, link.spec_id) for link in _state["result"].valid_links}
    assert ("d" * 40, "SPEC-010") in links, links
    assert ("d" * 40, "SPEC-011") in links, links
