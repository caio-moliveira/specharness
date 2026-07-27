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
    "ReadinessReport",
    "Scenario",
    "ScenarioRun",
    "Step",
    "VerifyReport",
    "allows_done",
    "done_edit_allowed",
    "evaluate_readiness",
    "is_ci",
    "parse_feature",
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
