"""Commit history from the local git CLI (SPEC-006, ADR-011).

Disciplined subprocess over `git`, not a native binding: the only requirement is
`git` on PATH. Trailers are extracted with the core's pure mirror
(`extract_spec_trailers`), and ADR-011's equivalence promise is pinned by a test
that runs this reader against a real repository.

The `run` callable is injectable so the contract test drives canned `git log`
output with no subprocess at all.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime
from pathlib import Path

from specharness_core.ports.repository import (
    Commit,
    RepoRef,
    RepositoryError,
    parse_github_remote,
)
from specharness_core.trailers import extract_spec_trailers

_UNIT = "\x1f"  # separates fields within a commit record
_RECORD = "\x1e"  # separates commit records — neither char appears in messages
_LOG_FORMAT = f"%H{_UNIT}%an{_UNIT}%aI{_UNIT}%B{_RECORD}"

RunGit = Callable[[list[str]], str]


class LocalGitCommitReader:
    """Implements the core `CommitReader` port over the git CLI."""

    def __init__(self, path: str | Path, run: RunGit | None = None) -> None:
        self._path = Path(path)
        self._run = run or self._run_git

    def _run_git(self, args: list[str]) -> str:
        try:
            proc = subprocess.run(
                ["git", "-C", str(self._path), *args],
                capture_output=True,
                text=True,
                check=True,
                # git emits UTF-8; decode it explicitly so a commit message with
                # acentos/emoji não quebra no Windows (default cp1252). ADR-011.
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise RepositoryError.for_repo(str(self._path), "git não encontrado no PATH") from exc
        except subprocess.CalledProcessError as exc:
            raise RepositoryError.for_repo(str(self._path), _first_line(exc.stderr)) from exc
        return proc.stdout

    def commits(self) -> Iterator[Commit]:
        output = self._run(["log", f"--format={_LOG_FORMAT}"])
        for raw in output.split(_RECORD):
            record = raw.strip("\n")
            if not record.strip():
                continue
            sha, author, authored, message = record.split(_UNIT, 3)
            yield Commit(
                sha=sha,
                author=author,
                authored_at=datetime.fromisoformat(authored),
                message=message,
                spec_trailers=tuple(extract_spec_trailers(message)),
            )

    def remote_ref(self, remote: str = "origin") -> RepoRef:
        """The GitHub coordinate of a remote, parsed from its URL."""
        url = self._run(["remote", "get-url", remote]).strip()
        return parse_github_remote(url)


def _first_line(text: str) -> str:
    stripped = text.strip()
    return stripped.splitlines()[0] if stripped else "erro do git"
