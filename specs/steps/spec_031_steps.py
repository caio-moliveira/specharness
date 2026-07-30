"""Step definitions da SPEC-031 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-031 --steps specs/steps/spec_031_steps.py`.
Roda o `connect repo` real via CliRunner com reader/cliente GitHub falsos
(mesmo padrão hermético de tests/test_connect_repo.py), em tmp dir com
SQLite próprio e GITHUB_TOKEN sintético.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from specharness_adapters.verify import StepRegistry
from specharness_cli import main
from specharness_core.ports.database import DATABASE_URL_ENV
from specharness_core.ports.repository import (
    Commit,
    PullRequest,
    RepoRef,
    RepositoryError,
)
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {}


class _FakeGitHubClient:
    def __init__(self, ref: RepoRef, token: str, **kwargs: Any) -> None:
        pass

    def pull_requests(self):
        yield PullRequest(
            number=1,
            title="t",
            state="open",
            head_branch="feat/x",
            base_branch="main",
            commit_shas=("a",),
        )


def _make_reader(parseable: bool):
    asked: list[str] = []

    class _Reader:
        remotes_asked = asked

        def __init__(self, path: Any, run: Any = None) -> None:
            pass

        def remote_ref(self, remote: str = "origin") -> RepoRef:
            asked.append(remote)
            if not parseable:
                raise RepositoryError("não reconheço a URL de remote do GitHub: 'proxy://x'")
            return RepoRef("acme", "tool")

        def commits(self):
            yield Commit(
                sha="a",
                author="Ana",
                authored_at=datetime(2026, 7, 30),
                message="feat: x\n\nSpec: SPEC-006",
                spec_trailers=("SPEC-006",),
            )

    return _Reader


def _run_connect(args: list[str]) -> None:
    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    saved_token = os.environ.get("GITHUB_TOKEN")
    originals = (main.LocalGitCommitReader, main.GitHubClient)
    os.environ["GITHUB_TOKEN"] = "ghp_sintetico"
    main.LocalGitCommitReader = _state["reader"]
    main.GitHubClient = _FakeGitHubClient
    tmp = Path(tempfile.mkdtemp(prefix="spec031-"))
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(main.app, ["connect", "repo", *args])
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        os.chdir(saved_cwd)
        main.LocalGitCommitReader, main.GitHubClient = originals
        if saved_token is None:
            os.environ.pop("GITHUB_TOKEN", None)
        else:
            os.environ["GITHUB_TOKEN"] = saved_token
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


@registry.step(r"um repositório git cujo remote upstream aponta para o GitHub")
def _given_upstream_remote() -> None:
    _state.clear()
    _state["reader"] = _make_reader(parseable=True)


@registry.step(r"um repositório git cujo remote origin tem URL irreconhecível")
def _given_unparseable_origin() -> None:
    _state.clear()
    _state["reader"] = _make_reader(parseable=False)


@registry.step(r"um repositório git com remote origin apontando para o GitHub")
def _given_github_origin() -> None:
    _state.clear()
    _state["reader"] = _make_reader(parseable=True)


@registry.step(r"o connect repo roda com --remote upstream")
def _when_connect_with_named_remote() -> None:
    _run_connect(["--remote", "upstream"])


@registry.step(r"o connect repo roda com --repo indicando owner e nome")
def _when_connect_with_repo_flag() -> None:
    _run_connect(["--repo", "acme/tool"])


@registry.step(r"o connect repo roda sem opções")
def _when_connect_plain() -> None:
    _run_connect([])


@registry.step(r"o repositório é resolvido a partir do remote upstream")
def _then_resolved_from_upstream() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _state["reader"].remotes_asked == ["upstream"], _state["reader"].remotes_asked


@registry.step(r"a ingestão usa o repositório informado sem consultar a URL do remote")
def _then_repo_flag_bypasses_parsing() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert "acme/tool" in _state["output"], _state["output"]
    assert _state["reader"].remotes_asked == [], _state["reader"].remotes_asked


@registry.step(r"o erro menciona as opções --remote e --repo como alternativas")
def _then_error_points_to_flags() -> None:
    assert _state["exit_code"] == 1, _state["output"]
    flat = " ".join(_state["output"].split())
    assert "--remote" in flat and "--repo" in flat, flat


@registry.step(r"o repositório é resolvido a partir do origin")
def _then_resolved_from_origin() -> None:
    assert _state["exit_code"] == 0, _state["output"]
    assert _state["reader"].remotes_asked == ["origin"], _state["reader"].remotes_asked
