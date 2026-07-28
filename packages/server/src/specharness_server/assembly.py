"""Assemble dashboard responses from core + stores (SPEC-016).

The server is a delivery layer, like the CLI: it reads the spec registry from disk
and the materialized data from the stores, and composes the read-only views. No
domain rule lives here — the counting and linking come from core (`link_commits`,
`aggregate_perception`), the numbers from the SPEC-013/014 stores.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from specharness_adapters.db import (
    MetricSnapshotStore,
    PerceptionStore,
    RepositoryStore,
    ScenarioRunStore,
)
from specharness_core import (
    SpecInfo,
    SpecParseError,
    aggregate_perception,
    link_commits,
    parse_spec,
)
from specharness_core.ports.database import DatabaseTarget

from .models import (
    BigPicture,
    Hygiene,
    PerceptionSummary,
    PipelineStage,
    SpecPipeline,
    SpecStatusCount,
    SprintMetricRow,
)

#: The dashboard is the first visible delivery of Fase A (SPEC-001 §5).
PHASE = "Fase A"

_READINESS_DONE = frozenset({"ready", "in_progress", "verifying", "done"})


def load_spec_infos(specs_dir: Path) -> list[SpecInfo]:
    """The spec registry from specs/*.md on disk (SPEC-003)."""
    infos: list[SpecInfo] = []
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        try:
            parsed = parse_spec(path.read_text(encoding="utf-8"))
        except SpecParseError:
            continue
        infos.append(
            SpecInfo(
                spec_id=parsed.spec_id,
                status=str(parsed.frontmatter.status),
                sprint=parsed.frontmatter.sprint,
            )
        )
    return infos


def current_sprint(infos: list[SpecInfo]) -> str | None:
    """The most recent sprint present in the registry (lexical max of the labels)."""
    sprints = sorted({i.sprint for i in infos if i.sprint})
    return sprints[-1] if sprints else None


def big_picture(
    target: DatabaseTarget,
    specs_dir: Path,
    sprint: str | None = None,
    data_source: str = "live",
) -> BigPicture:
    infos = load_spec_infos(specs_dir)
    chosen = sprint or current_sprint(infos)

    by_status = Counter(info.status for info in infos)
    specs_by_status = [
        SpecStatusCount(status=status, count=count) for status, count in sorted(by_status.items())
    ]

    snapshot = MetricSnapshotStore(target).latest(chosen) if chosen else None
    metrics = (
        [
            SprintMetricRow(
                spec_id=m.spec_id,
                status=next((i.status for i in infos if i.spec_id == m.spec_id), "?"),
                first_run_pass_rate=m.first_run_pass_rate,
                cycle_time_seconds=m.cycle_time_seconds,
                turnover_30d=m.turnover_30d,
                commits=m.commits,
            )
            for m in snapshot.specs
        ]
        if snapshot is not None
        else []
    )

    perception_store = PerceptionStore(target)
    cycle_times = (
        {
            s.spec_id: s.cycle_time_seconds
            for s in snapshot.specs
            if s.cycle_time_seconds is not None
        }
        if snapshot is not None
        else {}
    )
    agg = aggregate_perception(
        chosen or "",
        perception_store.samples_for_sprint(chosen) if chosen else [],
        perception_store.skips_for_sprint(chosen) if chosen else 0,
        cycle_times,
    )

    linking = link_commits(RepositoryStore(target).all_commits(), infos)

    return BigPicture(
        phase=PHASE,
        sprint=chosen,
        specs_by_status=specs_by_status,
        metrics=metrics,
        hygiene=Hygiene(
            orphan_commits=len(linking.orphan_commits),
            orphan_specs=len(linking.orphan_specs),
        ),
        perception=PerceptionSummary(
            n_samples=agg.n_samples,
            n_skipped=agg.n_skipped,
            aproveitamento_mean=agg.aproveitamento_mean,
            perception_gap=agg.perception_gap,
        ),
        data_source=data_source,
    )


def spec_pipeline(target: DatabaseTarget, specs_dir: Path, spec_id: str) -> SpecPipeline | None:
    infos = load_spec_infos(specs_dir)
    info = next((i for i in infos if i.spec_id == spec_id), None)
    if info is None:
        return None

    links = [
        link
        for link in link_commits(RepositoryStore(target).all_commits(), infos).valid_links
        if link.spec_id == spec_id
    ]
    events = ScenarioRunStore(target).events_for(spec_id)
    green = any(e.status == "passed" for e in events)
    samples = [
        s
        for s in PerceptionStore(target).samples_for_sprint(info.sprint or "")
        if s.spec_id == spec_id
    ]

    # detail é o fallback pt-BR; detail_key + count/value localizam na UI (SPEC-018)
    stages = [
        PipelineStage(
            stage="readiness",
            status="done" if info.status in _READINESS_DONE else "pending",
            detail=f"status: {info.status}",
            detail_key="detailSpecStatus",
            detail_value=info.status,
        ),
        PipelineStage(
            stage="commits",
            status="done" if links else "pending",
            detail=f"{len(links)} commit(s) vinculado(s)",
            detail_key="detailLinkedCommits",
            detail_count=len(links),
        ),
        PipelineStage(
            stage="bdd",
            status="done" if green else "pending",
            detail=f"{len(events)} execução(ões) de cenário registrada(s)",
            detail_key="detailScenarioRuns",
            detail_count=len(events),
        ),
        PipelineStage(
            stage="review",
            status="unavailable",
            detail="ingestão de eventos de review pendente (deferida na SPEC-013)",
            detail_key="detailReviewPending",
        ),
        PipelineStage(
            stage="perception",
            status="done" if samples else "pending",
            detail=f"{len(samples)} amostra(s) de percepção",
            detail_key="detailPerceptionSamples",
            detail_count=len(samples),
        ),
    ]
    return SpecPipeline(spec_id=spec_id, sprint=info.sprint, stages=stages)
