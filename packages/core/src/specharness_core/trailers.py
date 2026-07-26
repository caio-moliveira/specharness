"""Commit-message trailer parsing (SPEC-001 §7.3).

The `Spec:` git trailer is the source of truth for commit<->spec linking.
This is a pure function mirror of `git interpret-trailers` semantics for the
subset we need, so hooks and tests can run without shelling out. The `track`
module uses the real git CLI in production (ADR-011); both must agree — the
test suite pins that equivalence.
"""

from __future__ import annotations

import re

from .specschema import SPEC_ID_PATTERN

_TRAILER_RE = re.compile(r"^Spec:\s*(?P<value>\S+)\s*$", re.MULTILINE)


def extract_spec_trailers(message: str) -> list[str]:
    """Return all values of `Spec:` trailers found in a commit message.

    Trailers are only searched in the last paragraph block of the message,
    matching git's own trailer semantics.
    """
    paragraphs = [p for p in re.split(r"\n\s*\n", message.strip()) if p.strip()]
    if not paragraphs:
        return []
    return [m.group("value") for m in _TRAILER_RE.finditer(paragraphs[-1])]


def valid_spec_trailers(message: str) -> tuple[list[str], list[str]]:
    """Split extracted trailer values into (valid_ids, invalid_values)."""
    valid: list[str] = []
    invalid: list[str] = []
    for value in extract_spec_trailers(message):
        (valid if SPEC_ID_PATTERN.match(value) else invalid).append(value)
    return valid, invalid
