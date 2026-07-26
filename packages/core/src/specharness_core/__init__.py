"""specharness-core: the domain of specharness.

Pure Python, no I/O, no framework imports (ADR-001).
"""

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
