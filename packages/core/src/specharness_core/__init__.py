"""specharness-core: the domain of specharness.

Pure Python, no I/O, no framework imports (ADR-001).
"""

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

__all__ = [
    "AMBIGUOUS_TERMS",
    "CoverageRow",
    "Feature",
    "Finding",
    "ReadinessReport",
    "Scenario",
    "Step",
    "evaluate_readiness",
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
