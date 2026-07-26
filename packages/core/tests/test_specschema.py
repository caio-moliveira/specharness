"""Tests for the spec parser — the central contract (SPEC-003)."""

import contextlib

import pytest
from hypothesis import given
from hypothesis import strategies as st
from specharness_core import (
    SpecParseError,
    SpecStatus,
    can_transition,
    parse_spec,
)

VALID_SPEC = """\
---
spec: SPEC-042
title: "Busca por termo exato"
status: ready
type: feature
owner: joao
success_metrics:
  - "Latencia p95 < 800ms"
acceptance:
  - Busca retorna resultados com o termo destacado
---

## Contexto

Corpo da spec.

```gherkin
Funcionalidade: busca exata
  Cenario: termo presente
    Dado que a colecao contem o termo
    Quando o usuario busca no modo exato
    Entao o resultado destaca o termo
```
"""


def test_parses_valid_spec():
    parsed = parse_spec(VALID_SPEC)
    assert parsed.spec_id == "SPEC-042"
    assert parsed.frontmatter.status is SpecStatus.READY
    assert parsed.frontmatter.success_metrics == ["Latencia p95 < 800ms"]
    assert "## Contexto" in parsed.body


def test_extracts_gherkin_blocks():
    parsed = parse_spec(VALID_SPEC)
    blocks = parsed.gherkin_blocks
    assert len(blocks) == 1
    assert "Funcionalidade: busca exata" in blocks[0]


def test_rejects_document_without_frontmatter():
    with pytest.raises(SpecParseError, match="frontmatter"):
        parse_spec("# apenas markdown\n")


def test_rejects_invalid_spec_id():
    bad = VALID_SPEC.replace("SPEC-042", "SPEC42")
    with pytest.raises(SpecParseError, match="invalid spec id"):
        parse_spec(bad)


def test_rejects_invalid_status():
    bad = VALID_SPEC.replace("status: ready", "status: doing")
    with pytest.raises(SpecParseError):
        parse_spec(bad)


def test_rejects_invalid_dependency_id():
    bad = VALID_SPEC.replace("owner: joao", "owner: joao\ndepends_on: [SPEC-001, nonsense]")
    with pytest.raises(SpecParseError, match="depends_on"):
        parse_spec(bad)


def test_lifecycle_happy_path():
    order = [
        SpecStatus.DRAFT,
        SpecStatus.APPROVED,
        SpecStatus.READY,
        SpecStatus.IN_PROGRESS,
        SpecStatus.VERIFYING,
        SpecStatus.DONE,
        SpecStatus.ARCHIVED,
    ]
    for current, target in zip(order, order[1:], strict=False):
        assert can_transition(current, target)


def test_lifecycle_blocks_skipping_the_readiness_gate():
    assert not can_transition(SpecStatus.APPROVED, SpecStatus.IN_PROGRESS)
    assert not can_transition(SpecStatus.DRAFT, SpecStatus.DONE)
    assert not can_transition(SpecStatus.ARCHIVED, SpecStatus.DRAFT)


@given(st.text(max_size=2000))
def test_parser_never_crashes_unexpectedly(text):
    """Property: arbitrary input either parses or raises SpecParseError."""
    with contextlib.suppress(SpecParseError):
        parse_spec(text)
