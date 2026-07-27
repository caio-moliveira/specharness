"""Sprint test-hygiene signals from the git range (SPEC-013, ADR-016).

Attribution is by commit: each commit in `base..HEAD` carries its `Spec:` trailer
(SPEC-009) and its own diff, so a tampering signal in a commit's test changes is
tied to exactly the spec that commit belongs to. The pure detector lives in
`specharness_core.metrics.tampering_signals`; here we only feed it real diffs.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from specharness_core.metrics import HygieneSignal, tampering_signals
from specharness_core.trailers import extract_spec_trailers

from .git_metrics import _RECORD, _UNIT, _run_git

RunGit = Callable[[list[str]], str]


class SprintHygieneReader:
    """Collects test-tampering signals across a commit range, per spec."""

    def __init__(self, path: str | Path, run: RunGit | None = None) -> None:
        self._path = Path(path)
        self._run = run or (lambda args: _run_git(self._path, args))

    def signals(self, base: str) -> list[HygieneSignal]:
        log = self._run(["log", f"{base}..HEAD", f"--format=%H{_UNIT}%B{_RECORD}"])
        collected: list[HygieneSignal] = []
        for raw in log.split(_RECORD):
            record = raw.strip("\n")
            if _UNIT not in record:
                continue
            sha, message = record.split(_UNIT, 1)
            trailers = extract_spec_trailers(message)
            if not trailers:
                continue
            diff = self._run(["show", "--unified=0", "--format=", sha.strip()])
            for spec_id in trailers:
                collected.extend(tampering_signals(diff, spec_id))
        return collected
