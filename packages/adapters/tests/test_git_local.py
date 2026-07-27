"""The local git reader (SPEC-006, ADR-011).

Two layers: parsing is proven hermetically with canned `git log` output (a `run`
callable is injected, no subprocess), and a small real repository is created in
a tmp dir to pin ADR-011's equivalence — the real git CLI and the pure trailer
parser must agree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from specharness_adapters.git import LocalGitCommitReader
from specharness_core.ports.repository import RepositoryError

UNIT = "\x1f"
RECORD = "\x1e"


def _log(records: list[tuple[str, str, str, str]]) -> str:
    return "".join(
        f"{sha}{UNIT}{author}{UNIT}{iso}{UNIT}{message}{RECORD}\n"
        for sha, author, iso, message in records
    )


def _reader(run) -> LocalGitCommitReader:
    return LocalGitCommitReader("/repo", run=run)


# --- parsing hermético -----------------------------------------------------


def test_parses_commits_and_extracts_spec_trailers():
    output = _log(
        [
            ("abc123", "Ana", "2026-07-27T10:00:00-03:00", "feat: x\n\nSpec: SPEC-006"),
            ("def456", "Bob", "2026-07-26T09:00:00-03:00", "chore: sem trailer"),
        ]
    )

    commits = list(_reader(lambda args: output).commits())

    assert [c.sha for c in commits] == ["abc123", "def456"]
    assert commits[0].author == "Ana"
    assert commits[0].authored_at.year == 2026
    assert commits[0].spec_trailers == ("SPEC-006",)
    assert commits[1].spec_trailers == ()


def test_empty_history_yields_no_commits():
    assert list(_reader(lambda args: "").commits()) == []


def test_remote_ref_parses_the_origin_url():
    def run(args):
        assert args[:2] == ["remote", "get-url"]
        return "git@github.com:caio-moliveira/specharness.git\n"

    assert _reader(run).remote_ref().slug == "caio-moliveira/specharness"


# --- git real: erro e equivalência (ADR-011) -------------------------------


def test_a_non_repository_path_raises_repository_error(tmp_path):
    with pytest.raises(RepositoryError):
        list(LocalGitCommitReader(tmp_path).commits())


def test_missing_git_binary_raises_repository_error(monkeypatch, tmp_path):
    def boom(*args, **kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr("specharness_adapters.git.local.subprocess.run", boom)

    with pytest.raises(RepositoryError) as excinfo:
        list(LocalGitCommitReader(tmp_path).commits())

    assert "git" in str(excinfo.value).lower()


def _init_repo(path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", "-C", str(path), *args], check=True, capture_output=True, text=True)

    subprocess.run(["git", "init", "-q", str(path)], check=True, capture_output=True, text=True)
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "Tester")
    git("commit", "--allow-empty", "-m", "feat: primeiro\n\nSpec: SPEC-006")
    git("commit", "--allow-empty", "-m", "chore: segundo sem trailer")


def test_real_git_reads_commits_and_agrees_with_the_pure_trailer_parser(tmp_path):
    _init_repo(tmp_path)

    commits = list(LocalGitCommitReader(tmp_path).commits())

    assert len(commits) == 2
    trailers = [c.spec_trailers for c in commits]
    assert ("SPEC-006",) in trailers  # o commit com trailer foi extraído
    assert () in trailers  # o sem trailer não inventou nada
