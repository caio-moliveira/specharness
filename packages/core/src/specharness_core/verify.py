"""BDD verify gate — the door to `done` (SPEC-012, ADR-016).

Pure domain (ADR-001): the *result* of running a spec's scenarios and the
*verdicts* around it. Running the scenarios against step definitions is I/O and
lives in an adapter; here we only know what a run is, when it blocks `done`, and
when a `done` edit is allowed at all.

A spec is `done` only with proven behaviour (SPEC-001 §7.2). The CI is the sole
arbiter: whoever implements does not arbitrate (ADR-016).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .specschema import SpecStatus, can_transition

ScenarioStatus = Literal["passed", "failed", "pending"]


@dataclass(frozen=True)
class ScenarioRun:
    """One scenario's outcome (SPEC-012, critério 2)."""

    spec_id: str
    scenario_title: str
    status: ScenarioStatus
    first_run: bool = False


@dataclass(frozen=True)
class VerifyReport:
    """Every scenario's outcome for a spec, and the verdict it implies."""

    spec_id: str
    runs: tuple[ScenarioRun, ...]

    @property
    def passed(self) -> tuple[ScenarioRun, ...]:
        return tuple(r for r in self.runs if r.status == "passed")

    @property
    def failed(self) -> tuple[ScenarioRun, ...]:
        return tuple(r for r in self.runs if r.status == "failed")

    @property
    def pending(self) -> tuple[ScenarioRun, ...]:
        return tuple(r for r in self.runs if r.status == "pending")

    @property
    def all_green(self) -> bool:
        """True only if there is at least one scenario and all passed."""
        return bool(self.runs) and not self.failed and not self.pending


def is_ci(env: Mapping[str, str]) -> bool:
    """Whether we are running in CI — the only arbiter of `done` (ADR-016)."""
    return env.get("CI", "").lower() in {"true", "1"}


def allows_done(current: SpecStatus, report: VerifyReport) -> bool:
    """verifying -> done is allowed only if the lifecycle permits it AND every
    scenario is green (critério 3)."""
    return can_transition(current, SpecStatus.DONE) and report.all_green


def done_edit_allowed(
    new_status: SpecStatus, previous_status: SpecStatus | None, *, in_ci: bool
) -> bool:
    """Whether editing a spec's status to `done` is allowed (ADR-016, critério 6).

    A transition *into* `done` is CI-only; a spec that was already `done` is not
    blocked (it is not a transition). Outside CI, moving to `done` is rejected.
    """
    if new_status != SpecStatus.DONE:
        return True
    if in_ci:
        return True
    return previous_status == SpecStatus.DONE
