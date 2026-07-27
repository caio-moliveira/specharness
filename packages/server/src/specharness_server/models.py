"""Response models — the OpenAPI contract for the dashboard (SPEC-016, ADR-014).

These Pydantic models ARE the contract: the web client is generated from the
OpenAPI schema FastAPI derives from them, so a shape change here breaks the web
build, not runtime (ADR-014). The server is a delivery layer — it holds no domain
rule, only the shapes the read-only dashboard needs.
"""

from __future__ import annotations

from pydantic import BaseModel


class SpecStatusCount(BaseModel):
    status: str
    count: int


class SprintMetricRow(BaseModel):
    spec_id: str
    status: str
    first_run_pass_rate: float | None
    cycle_time_seconds: float | None
    turnover_30d: float | None
    commits: int


class Hygiene(BaseModel):
    orphan_commits: int
    orphan_specs: int


class PerceptionSummary(BaseModel):
    n_samples: int
    n_skipped: int
    aproveitamento_mean: float | None
    perception_gap: float | None


class BigPicture(BaseModel):
    phase: str
    sprint: str | None
    specs_by_status: list[SpecStatusCount]
    metrics: list[SprintMetricRow]
    hygiene: Hygiene
    perception: PerceptionSummary


class PipelineStage(BaseModel):
    stage: str
    status: str  # done | pending | unavailable
    detail: str


class SpecPipeline(BaseModel):
    spec_id: str
    sprint: str | None
    stages: list[PipelineStage]
