"""Sprint report — the pure domain (SPEC-015, ADR-006).

The Fase 6 deliverable someone writes by hand today. The *content* is
deterministic: assembled from already-materialized data (the SPEC-013 metrics
snapshot, the SPEC-014 perception aggregate, the SPEC-009 linking) and rendered to
markdown here, with no I/O. The LLM only writes prose — and this module also holds
the guard that keeps the prose honest: `narrative_divergences` is the product's
read-before-cite, extracting every number a narrative cites and refusing any that
does not appear verbatim in the tabular data.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .linking import LinkingResult
from .metrics import SpecMetrics, SprintSnapshot
from .perception import SprintPerception

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?%?")


@dataclass(frozen=True)
class ReportRow:
    """One spec's line in the tabular report."""

    spec_id: str
    status: str
    first_run_pass_rate: float | None
    cycle_time_seconds: float | None
    turnover_30d: float | None
    commits: int


@dataclass(frozen=True)
class SprintReport:
    """The assembled sprint report — content only, no rendering decisions."""

    sprint: str
    rows: tuple[ReportRow, ...]
    n_planejadas: int
    n_concluidas: int
    orphan_commits: tuple[str, ...]
    orphan_specs: tuple[str, ...]
    perception: SprintPerception


def build_report(
    sprint: str,
    snapshot: SprintSnapshot | None,
    perception: SprintPerception,
    linking: LinkingResult,
    spec_statuses: Mapping[str, str],
) -> SprintReport:
    """Assemble the sprint report from the raw materialized data.

    `spec_statuses` is the sprint's specs (planned); a spec in `done` is counted as
    concluded. Metrics come from the snapshot when present, else null.
    """
    metrics: dict[str, SpecMetrics] = (
        {m.spec_id: m for m in snapshot.specs} if snapshot is not None else {}
    )
    rows: list[ReportRow] = []
    for spec_id in sorted(spec_statuses):
        metric = metrics.get(spec_id)
        rows.append(
            ReportRow(
                spec_id=spec_id,
                status=spec_statuses[spec_id],
                first_run_pass_rate=metric.first_run_pass_rate if metric else None,
                cycle_time_seconds=metric.cycle_time_seconds if metric else None,
                turnover_30d=metric.turnover_30d if metric else None,
                commits=metric.commits if metric else 0,
            )
        )
    concluidas = sum(1 for status in spec_statuses.values() if status == "done")
    return SprintReport(
        sprint=sprint,
        rows=tuple(rows),
        n_planejadas=len(spec_statuses),
        n_concluidas=concluidas,
        orphan_commits=linking.orphan_commits,
        orphan_specs=linking.orphan_specs,
        perception=perception,
    )


def render_markdown(report: SprintReport) -> str:
    """Render the report to deterministic markdown (the default output)."""
    p = report.perception
    lines = [
        f"# Relatório da sprint {report.sprint}",
        "",
        f"- Specs planejadas: {report.n_planejadas}",
        f"- Specs concluídas: {report.n_concluidas}",
        f"- Commits órfãos: {len(report.orphan_commits)}",
        f"- Specs órfãs: {len(report.orphan_specs)}",
        "",
        "## Métricas por spec",
        "",
        "| Spec | Status | First-run | Cycle time | Turnover 30d | Commits |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in report.rows:
        lines.append(
            f"| {row.spec_id} | {row.status} | {_pct(row.first_run_pass_rate)} | "
            f"{_hours(row.cycle_time_seconds)} | {_ratio(row.turnover_30d)} | {row.commits} |"
        )
    lines += [
        "",
        "## Percepção",
        "",
        f"- Amostras: {p.n_samples} · Skips: {p.n_skipped}",
        f"- Aproveitamento médio: {_mean(p.aproveitamento_mean)}",
        f"- Gap de percepção: {_pct(p.perception_gap)}",
    ]
    return "\n".join(lines)


def extract_numbers(text: str) -> set[str]:
    """Every numeric token in a text (integers, decimals, percentages)."""
    return {m.group(0) for m in _NUMBER_RE.finditer(text)}


def narrative_divergences(narrative: str, report: SprintReport) -> list[str]:
    """Numbers a narrative cites that do not appear in the tabular data (read-before-cite).

    A non-empty result means the narrative invented a number and must be rejected
    (SPEC-015, acceptance / cenário "número divergente é rejeitada").
    """
    allowed = extract_numbers(render_markdown(report))
    cited = extract_numbers(narrative)
    return sorted(cited - allowed)


def is_faithful(narrative: str, report: SprintReport) -> bool:
    """True when every number in the narrative is backed by the tabular data."""
    return not narrative_divergences(narrative, report)


# --- rendering helpers ------------------------------------------------------


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.0f}%"


def _ratio(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def _hours(value: float | None) -> str:
    return "—" if value is None else f"{value / 3600:.1f}h"


def _mean(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}"


def report_lines(report: SprintReport) -> Sequence[str]:
    """The markdown as a list of lines — what the docx export writes as paragraphs."""
    return render_markdown(report).split("\n")
