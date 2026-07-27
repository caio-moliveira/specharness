"""Camada-2 raw signals read from the local git CLI (SPEC-013, ADR-001/ADR-011).

Two readers, both disciplined subprocess over `git` (the only dependency is
`git` on PATH), both feeding the pure `specharness_core.metrics` domain:

- `StatusHistoryReader` reconstructs a spec's status transitions from the git
  history of its frontmatter — every commit that changed the `status:` line is a
  transition with the commit's authored timestamp. That is the raw artifact the
  cycle-time metric needs, with no separate event log to maintain (ADR-016: the
  timestamp comes from git, not from anything an agent reports).
- `TurnoverReader` measures line survival by `git blame` in a window (success
  metric 2): of the lines a spec's commits added, how many are still attributed
  to those commits at HEAD. The repo baseline is the same measure over every
  commit in the window, so the ratio compares like with like.

`run` is injectable so error paths and parsing can be driven hermetically; the
survival arithmetic is pinned against real temporary repositories.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from specharness_core.metrics import StatusTransition
from specharness_core.ports.repository import RepositoryError
from specharness_core.specschema import SpecStatus
from specharness_core.trailers import extract_spec_trailers

RunGit = Callable[[list[str]], str]

_UNIT = "\x1f"
_RECORD = "\x1e"
_STATUS_RE = re.compile(r"^status:\s*([A-Za-z_]+)\s*$", re.MULTILINE)
_SHA_LINE_RE = re.compile(r"^([0-9a-f]{40}) ")


def _run_git(path: Path, args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RepositoryError.for_repo(str(path), "git não encontrado no PATH") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "erro do git").strip().splitlines()
        raise RepositoryError.for_repo(str(path), detail[0] if detail else "erro do git") from exc
    return proc.stdout


class StatusHistoryReader:
    """Reconstructs a spec's status transitions from its frontmatter history."""

    def __init__(self, path: str | Path, spec_relpath: str, run: RunGit | None = None) -> None:
        self._path = Path(path)
        self._spec_relpath = spec_relpath
        self._run = run or (lambda args: _run_git(self._path, args))

    def transitions(self, spec_id: str) -> list[StatusTransition]:
        log = self._run(["log", "--reverse", f"--format=%H{_UNIT}%aI", "--", self._spec_relpath])
        result: list[StatusTransition] = []
        previous: SpecStatus | None = None
        for line in log.splitlines():
            if _UNIT not in line:
                continue
            sha, iso = line.split(_UNIT, 1)
            content = self._run(["show", f"{sha}:{self._spec_relpath}"])
            status = self._status_of(content)
            if status is not None and status != previous:
                result.append(StatusTransition(spec_id, status, datetime.fromisoformat(iso)))
                previous = status
        return result

    @staticmethod
    def _status_of(content: str) -> SpecStatus | None:
        match = _STATUS_RE.search(content)
        if match is None:
            return None
        try:
            return SpecStatus(match.group(1))
        except ValueError:
            return None


class TurnoverReader:
    """Blame-based line survival for a spec and the repo baseline in a window."""

    def __init__(self, path: str | Path, run: RunGit | None = None) -> None:
        self._path = Path(path)
        self._run = run or (lambda args: _run_git(self._path, args))

    def turnover(self, spec_id: str, *, window_days: int, as_of: datetime) -> float | None:
        shas = self._spec_commits(spec_id, window_days=window_days, as_of=as_of)
        return self._survival_turnover(shas)

    def repo_baseline(self, *, window_days: int, as_of: datetime) -> float | None:
        shas = self._commits_in_window(window_days=window_days, as_of=as_of)
        return self._survival_turnover(shas)

    # -- internals -----------------------------------------------------------

    def _survival_turnover(self, shas: set[str]) -> float | None:
        """1 - surviving/added: the fraction of the shas' added lines rewritten."""
        if not shas:
            return None
        added, files = self._added_lines_and_files(shas)
        if added == 0:
            return None
        surviving = sum(self._surviving_lines(path, shas) for path in files)
        return 1.0 - surviving / added

    def _commits_in_window(self, *, window_days: int, as_of: datetime) -> set[str]:
        since = (as_of - timedelta(days=window_days)).isoformat()
        until = as_of.isoformat()
        out = self._run(["log", "--format=%H", f"--since={since}", f"--until={until}"])
        return {line.strip() for line in out.splitlines() if line.strip()}

    def _spec_commits(self, spec_id: str, *, window_days: int, as_of: datetime) -> set[str]:
        since = (as_of - timedelta(days=window_days)).isoformat()
        until = as_of.isoformat()
        out = self._run(
            [
                "log",
                f"--format=%H{_UNIT}%B{_RECORD}",
                f"--since={since}",
                f"--until={until}",
            ]
        )
        shas: set[str] = set()
        for raw in out.split(_RECORD):
            record = raw.strip("\n")
            if _UNIT not in record:
                continue
            sha, message = record.split(_UNIT, 1)
            if spec_id in extract_spec_trailers(message):
                shas.add(sha.strip())
        return shas

    def _added_lines_and_files(self, shas: set[str]) -> tuple[int, set[str]]:
        added = 0
        files: set[str] = set()
        for sha in shas:
            out = self._run(["show", "--numstat", "--format=", sha])
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) != 3 or parts[0] == "-":  # binário: '-\t-\tpath'
                    continue
                added += int(parts[0])
                files.add(parts[2])
        return added, files

    def _surviving_lines(self, path: str, shas: set[str]) -> int:
        try:
            blame = self._run(["blame", "--line-porcelain", "HEAD", "--", path])
        except RepositoryError:
            return 0  # arquivo removido até HEAD: nenhuma linha sobrevive
        return sum(
            1
            for line in blame.splitlines()
            if (m := _SHA_LINE_RE.match(line)) and m.group(1) in shas
        )
