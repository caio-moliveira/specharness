"""Commit-message trailer parsing (SPEC-001 §7.3).

The `Spec:` git trailer is the source of truth for commit<->spec linking.
This is a pure mirror of `git interpret-trailers` semantics for the subset we
need, so hooks and tests run without shelling out — and the equivalence suite
(SPEC-009, ADR-011) pins that the two genuinely agree.

git's rule (with no configured trailers): the trailer block is the last
paragraph, it must be preceded by a blank line (so a subject-only message has
none), and *every* non-blank line in it must be a trailer — a continuation line
(leading whitespace) only counts after a trailer. A single prose line in the
final block means git sees no trailers at all, so neither do we.
"""

from __future__ import annotations

import re

from .specschema import SPEC_ID_PATTERN

_TRAILER_RE = re.compile(r"^Spec:\s*(?P<value>\S+)\s*$", re.MULTILINE)
# A trailer line: `Token: value`, token being letters/digits/hyphens.
_TRAILER_LINE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*:\s")


def _is_trailer_block(block: str) -> bool:
    """True if every line is a trailer (mirroring git's rule).

    A paragraph never contains blank lines (they split paragraphs), so each line
    is either a trailer, or a continuation (leading whitespace) that only counts
    after a trailer.
    """
    seen_trailer = False
    for line in block.splitlines():
        if line[:1] in (" ", "\t"):
            if not seen_trailer:
                return False  # a continuation line with no trailer before it
            continue
        if not _TRAILER_LINE_RE.match(line):
            return False
        seen_trailer = True
    return seen_trailer


def extract_spec_trailers(message: str) -> list[str]:
    """Return all values of `Spec:` trailers in the message's trailer block.

    Agrees with `git interpret-trailers --parse`: the values live in the last
    paragraph, which must be preceded by a blank line and be a pure trailer block.
    """
    paragraphs = [p for p in re.split(r"\n\s*\n", message.strip()) if p.strip()]
    if len(paragraphs) < 2:  # subject-only: git sees no trailer block, nor do we
        return []
    block = paragraphs[-1]
    if not _is_trailer_block(block):
        return []
    return [m.group("value") for m in _TRAILER_RE.finditer(block)]


def valid_spec_trailers(message: str) -> tuple[list[str], list[str]]:
    """Split extracted trailer values into (valid_ids, invalid_values)."""
    valid: list[str] = []
    invalid: list[str] = []
    for value in extract_spec_trailers(message):
        (valid if SPEC_ID_PATTERN.match(value) else invalid).append(value)
    return valid, invalid
