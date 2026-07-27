"""Objective camada-2 metrics — the pure domain (SPEC-013, ADR-001).

Every function here is deterministic over already-materialized raw events: given
the same events it returns the same numbers, which is exactly what the "recálculo
é determinístico" acceptance demands (a snapshot recomputed from the events must
equal the original). No git, no database, no clock — collecting the raw artifacts
is the adapter's job (`specharness_adapters.metrics`).

Two invariants are structural here, not guidelines:

- **ADR-016 (quem implementa não arbitra).** The inputs are raw artifacts (git,
  CI, tracker). A number an agent reports about itself is never an input — there
  is deliberately no parameter through which self-reported coverage could enter.
- **ADR-008 (anti-vigilância).** `is_individual_query` names the axes that would
  expose an individual so the query layer can refuse them, and `paired_view`
  drops any volume metric shown without a quality metric beside it.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from .specschema import SpecStatus

MetricKind = Literal["volume", "quality"]
ScenarioOutcome = Literal["passed", "failed", "pending"]

#: Aggregation axes that would single out a person. A query touching any of these
#: is refused (ADR-008); the minimum aggregation is spec/sprint/team.
INDIVIDUAL_AXES: frozenset[str] = frozenset(
    {"author", "committer", "assignee", "user", "individual", "person", "developer"}
)


@dataclass(frozen=True)
class StatusTransition:
    """A spec's status change, as read from the git history of its frontmatter."""

    spec_id: str
    to_status: SpecStatus
    at: datetime


@dataclass(frozen=True)
class ScenarioRunEvent:
    """One recorded BDD outcome (a projection of a `scenario_runs` row)."""

    at: datetime
    status: ScenarioOutcome
    first_run: bool


@dataclass(frozen=True)
class HygieneSignal:
    """A test-hygiene signal attributed to a spec (ADR-016)."""

    spec_id: str
    kind: Literal["assert-removed", "naked-skip"]
    detail: str


@dataclass(frozen=True)
class MetricValue:
    """A single metric in a snapshot, tagged as volume or quality.

    A volume metric names, via `paired_with`, the quality metric it may only be
    shown alongside — `paired_view` enforces the pairing (ADR-008).
    """

    name: str
    kind: MetricKind
    value: float | None
    paired_with: str | None = None


@dataclass(frozen=True)
class SpecMetrics:
    """The objective metrics computed for a single spec in a sprint."""

    spec_id: str
    cycle_time_seconds: float | None
    first_run_pass_rate: float | None
    iterations_to_green: int | None
    turnover_30d: float | None
    turnover_90d: float | None
    turnover_ratio_30d: float | None
    turnover_ratio_90d: float | None
    commits: int


@dataclass(frozen=True)
class SprintSnapshot:
    """An immutable snapshot of a sprint's metrics.

    Value-compared (frozen dataclass over tuples): recomputing from the same raw
    events yields an equal snapshot, which is how determinism is verified.
    """

    sprint: str
    specs: tuple[SpecMetrics, ...]
    hygiene: tuple[HygieneSignal, ...] = field(default_factory=tuple)


# --- per-spec execution metrics (from git transitions + scenario_runs) ------


def cycle_time_seconds(transitions: Sequence[StatusTransition]) -> float | None:
    """Seconds from the first `ready` to the `done` of a spec.

    Measures lead time including any rework: if the spec bounced back out of
    `ready`, the clock still starts at the first time it became ready. Returns
    None when the spec never reached done (or the history is inconsistent).
    """
    ready_at = next((t.at for t in transitions if t.to_status is SpecStatus.READY), None)
    done_at = next((t.at for t in transitions if t.to_status is SpecStatus.DONE), None)
    if ready_at is None or done_at is None or done_at < ready_at:
        return None
    return (done_at - ready_at).total_seconds()


def first_run_pass_rate(events: Sequence[ScenarioRunEvent]) -> float | None:
    """Fraction of first-run scenarios that passed — the métrica-mãe da camada 2.

    Only events marked `first_run` count (the first CI run after ready, SPEC-012).
    Returns None when the spec has no first run recorded yet.
    """
    first = [e for e in events if e.first_run]
    if not first:
        return None
    passed = sum(1 for e in first if e.status == "passed")
    return passed / len(first)


def iterations_to_green(events: Sequence[ScenarioRunEvent]) -> int | None:
    """How many CI executions until every scenario passed.

    Each distinct timestamp is one execution. Returns the 1-based index of the
    first all-green execution, or None if the spec never went fully green.
    """
    by_execution: dict[datetime, list[ScenarioRunEvent]] = {}
    for event in events:
        by_execution.setdefault(event.at, []).append(event)
    for index, at in enumerate(sorted(by_execution), start=1):
        batch = by_execution[at]
        if batch and all(e.status == "passed" for e in batch):
            return index
    return None


def turnover_ratio(spec_turnover: float | None, repo_baseline: float | None) -> float | None:
    """The spec's turnover as a ratio over the repo's baseline churn.

    None when either side is missing or the baseline is zero (a repo with no
    churn in the window gives no meaningful denominator — reported indisponível).
    """
    if spec_turnover is None or repo_baseline is None or repo_baseline <= 0.0:
        return None
    return spec_turnover / repo_baseline


# --- anti-surveillance and volume/quality pairing (ADR-008) -----------------


def is_individual_query(dimensions: Sequence[str]) -> bool:
    """True if any aggregation axis would expose an individual (ADR-008)."""
    return any(dim.strip().lower() in INDIVIDUAL_AXES for dim in dimensions)


def paired_view(values: Sequence[MetricValue]) -> list[MetricValue]:
    """Drop volume metrics not shown alongside their quality pair (ADR-008).

    Quality metrics always pass through. A volume metric survives only if the
    quality metric it declares in `paired_with` is present in the same view.
    """
    present = {v.name for v in values if v.kind == "quality"}
    kept: list[MetricValue] = []
    for value in values:
        if (
            value.kind == "quality"
            or value.paired_with is not None
            and value.paired_with in present
        ):
            kept.append(value)
    return kept


# --- test-hygiene signals (ADR-016) -----------------------------------------

_ASSERT_RE = re.compile(r"^\s*assert\b")
_SKIP_RE = re.compile(r"pytest\.mark\.(skip|skipif|xfail)|\bunittest\.skip")
_REASON_RE = re.compile(r"reason\s*=")


def tampering_signals(diff_text: str, spec_id: str) -> list[HygieneSignal]:
    """Extract test-tampering signals from a unified diff (pure mirror of the CI gate).

    Same rule as `scripts/test_integrity.py`: in files under a `tests/` path, a
    net removal of asserts and any skip/xfail added without `reason=` are signals.
    Attribution to `spec_id` is the caller's (from the PR's Spec trailers).
    """
    current: str | None = None
    removed: dict[str, int] = {}
    added: dict[str, int] = {}
    naked_skips: list[str] = []
    for line in diff_text.splitlines():
        if line.startswith("diff --git"):
            current = line.split(" b/")[-1]
            continue
        if current is None or "/tests/" not in current:
            continue
        if line.startswith("-") and not line.startswith("---"):
            if _ASSERT_RE.match(line[1:]):
                removed[current] = removed.get(current, 0) + 1
        elif line.startswith("+") and not line.startswith("+++"):
            body = line[1:]
            if _ASSERT_RE.match(body):
                added[current] = added.get(current, 0) + 1
            if _SKIP_RE.search(body) and not _REASON_RE.search(body):
                naked_skips.append(body.strip())
    signals: list[HygieneSignal] = []
    for path in sorted(removed):
        net = removed[path] - added.get(path, 0)
        if net > 0:
            signals.append(
                HygieneSignal(
                    spec_id, "assert-removed", f"{path}: {net} assert(s) em saldo líquido"
                )
            )
    for snippet in naked_skips:
        signals.append(HygieneSignal(spec_id, "naked-skip", snippet))
    return signals


def hygiene_report(signals: Sequence[HygieneSignal]) -> dict[str, list[HygieneSignal]]:
    """Group hygiene signals by spec, sorted, for the sprint report."""
    report: dict[str, list[HygieneSignal]] = {}
    for signal in signals:
        report.setdefault(signal.spec_id, []).append(signal)
    return {spec_id: report[spec_id] for spec_id in sorted(report)}


# --- volume/quality helper for a spec's snapshot ----------------------------


def spec_metric_values(spec: SpecMetrics) -> list[MetricValue]:
    """Expose a spec's metrics as volume/quality-tagged values for `paired_view`.

    `commits` is the volume signal; it is paired with `first_run_pass_rate`, its
    quality counterpart — a raw commit count is never shown on its own (ADR-008).
    """
    return [
        MetricValue("first_run_pass_rate", "quality", spec.first_run_pass_rate),
        MetricValue("turnover_30d", "quality", spec.turnover_30d),
        MetricValue("cycle_time_seconds", "quality", spec.cycle_time_seconds),
        MetricValue("commits", "volume", float(spec.commits), paired_with="first_run_pass_rate"),
    ]
