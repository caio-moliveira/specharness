"""specharness-core: the domain of specharness.

Pure Python, no I/O, no framework imports (ADR-001).
"""

from .assessment import (
    DEFAULT_THRESHOLD,
    Evaluation,
    Override,
    ReadinessAssessment,
    ReadinessIssue,
    content_hash,
)
from .gherkin import Feature, Scenario, Step, parse_feature
from .linking import Link, LinkingResult, SpecInfo, link_commits
from .metrics import (
    HygieneSignal,
    MetricValue,
    ScenarioRunEvent,
    SpecMetrics,
    SprintSnapshot,
    StatusTransition,
    cycle_time_seconds,
    first_run_pass_rate,
    hygiene_report,
    is_individual_query,
    iterations_to_green,
    paired_view,
    spec_metric_values,
    tampering_signals,
    turnover_ratio,
)
from .readiness import (
    AMBIGUOUS_TERMS,
    CoverageRow,
    Finding,
    ReadinessReport,
    evaluate_readiness,
)
from .specschema import (
    ParsedSpec,
    SpecFrontmatter,
    SpecParseError,
    SpecStatus,
    SpecType,
    can_transition,
    parse_spec,
)
from .trailers import extract_spec_trailers, valid_spec_trailers
from .verify import (
    ScenarioRun,
    VerifyReport,
    allows_done,
    done_edit_allowed,
    is_ci,
)

__all__ = [
    "DEFAULT_THRESHOLD",
    "Evaluation",
    "Override",
    "ReadinessAssessment",
    "ReadinessIssue",
    "content_hash",
    "AMBIGUOUS_TERMS",
    "CoverageRow",
    "Feature",
    "Finding",
    "HygieneSignal",
    "MetricValue",
    "ReadinessReport",
    "Scenario",
    "ScenarioRun",
    "ScenarioRunEvent",
    "SpecMetrics",
    "SprintSnapshot",
    "StatusTransition",
    "Step",
    "VerifyReport",
    "allows_done",
    "cycle_time_seconds",
    "done_edit_allowed",
    "evaluate_readiness",
    "first_run_pass_rate",
    "hygiene_report",
    "is_ci",
    "is_individual_query",
    "iterations_to_green",
    "paired_view",
    "parse_feature",
    "spec_metric_values",
    "tampering_signals",
    "turnover_ratio",
    "Link",
    "LinkingResult",
    "SpecInfo",
    "link_commits",
    "ParsedSpec",
    "SpecFrontmatter",
    "SpecParseError",
    "SpecStatus",
    "SpecType",
    "can_transition",
    "parse_spec",
    "extract_spec_trailers",
    "valid_spec_trailers",
]

__version__ = "0.1.0"
