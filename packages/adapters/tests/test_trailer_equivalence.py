"""Equivalence: pure parser vs `git interpret-trailers` (SPEC-009, métrica 2, ADR-011).

ADR-011 promises the internal pure parser (`extract_spec_trailers`) agrees with
the real git trailer machinery. This suite pins that: for a set of well-formed
commit messages, the `Spec:` values git extracts equal what the pure parser
extracts.
"""

from __future__ import annotations

import subprocess

import pytest
from specharness_core.trailers import extract_spec_trailers

MESSAGES = [
    "feat: uma coisa\n\nSpec: SPEC-042",
    "feat: duas specs\n\nSpec: SPEC-010\nSpec: SPEC-011",
    "chore: sem trailer nenhum",
    "fix: com corpo\n\nUm parágrafo de corpo explicando.\n\nSpec: SPEC-100",
    "docs: valor mal-formado ainda é trailer\n\nSpec: SPEC-abc",
    "feat: trailer misturado com outros\n\nCo-Authored-By: Ana <a@x>\nSpec: SPEC-007",
]


def _git_interpret_spec_values(message: str) -> list[str]:
    proc = subprocess.run(
        ["git", "interpret-trailers", "--parse"],
        input=message,
        capture_output=True,
        text=True,
        check=True,
    )
    values: list[str] = []
    for line in proc.stdout.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() == "Spec":
            values.append(value.strip())
    return values


@pytest.mark.parametrize("message", MESSAGES)
def test_pure_parser_agrees_with_git_interpret_trailers(message):
    assert extract_spec_trailers(message) == _git_interpret_spec_values(message)
