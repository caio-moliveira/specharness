"""Tests for the spec parser — the central contract (SPEC-003)."""

import contextlib

import pytest
from hypothesis import given, settings
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
depends_on: [SPEC-001]
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


TWO_GHERKIN_SPEC = """\
---
spec: SPEC-043
title: "Spec com dois blocos"
---

## Cenarios (BDD)

```gherkin
Funcionalidade: primeira
  Cenario: um
    Quando algo acontece
    Entao algo e verificado
```

Texto entre os blocos.

```gherkin
Funcionalidade: segunda
  Cenario: dois
    Quando outra coisa acontece
    Entao outra coisa e verificada
```
"""


def test_parses_valid_spec():
    parsed = parse_spec(VALID_SPEC)
    assert parsed.spec_id == "SPEC-042"
    assert parsed.frontmatter.status is SpecStatus.READY
    assert parsed.frontmatter.success_metrics == ["Latencia p95 < 800ms"]
    assert parsed.frontmatter.depends_on == ["SPEC-001"]
    assert "## Contexto" in parsed.body


def test_extracts_gherkin_blocks():
    parsed = parse_spec(VALID_SPEC)
    blocks = parsed.gherkin_blocks
    assert len(blocks) == 1
    assert "Funcionalidade: busca exata" in blocks[0]


def test_extracts_two_gherkin_blocks():
    """Cenario: blocos gherkin sao extraidos do corpo (exatamente dois)."""
    blocks = parse_spec(TWO_GHERKIN_SPEC).gherkin_blocks
    assert len(blocks) == 2
    assert "Funcionalidade: primeira" in blocks[0]
    assert "Funcionalidade: segunda" in blocks[1]
    assert "Texto entre os blocos" not in blocks[0]


def test_rejects_document_without_frontmatter():
    with pytest.raises(SpecParseError, match="frontmatter"):
        parse_spec("# apenas markdown\n")


def test_rejects_syntactically_invalid_yaml():
    """Cenario: frontmatter com YAML invalido.

    Asserta "invalid YAML" e nao apenas "YAML": a mensagem de frontmatter
    que nao e mapping tambem contem "YAML", e passaria por acidente.
    """
    bad = '---\nspec: SPEC-042\ntitle: "aspas nao fechadas\n---\n\nCorpo.\n'
    with pytest.raises(SpecParseError, match="invalid YAML"):
        parse_spec(bad)


def test_rejects_frontmatter_that_is_not_a_mapping():
    bad = "---\napenas uma string solta\n---\n\nCorpo.\n"
    with pytest.raises(SpecParseError, match="mapping"):
        parse_spec(bad)


def test_rejects_invalid_spec_id():
    bad = VALID_SPEC.replace("SPEC-042", "SPEC42")
    with pytest.raises(SpecParseError, match="invalid spec id"):
        parse_spec(bad)


def test_rejects_invalid_status():
    bad = VALID_SPEC.replace("status: ready", "status: doing")
    with pytest.raises(SpecParseError, match="status"):
        parse_spec(bad)


def test_rejects_invalid_dependency_id():
    # Substitui a linha existente: injetar uma segunda chave `depends_on`
    # criaria YAML com chave duplicada, e a ultima venceria silenciosamente.
    bad = VALID_SPEC.replace("depends_on: [SPEC-001]", "depends_on: [SPEC-001, nonsense]")
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


def test_lifecycle_allows_one_step_rollback():
    """Cenario: rollback de um passo e aceito (desvio D2 de SPEC-001 §7.2)."""
    assert can_transition(SpecStatus.VERIFYING, SpecStatus.IN_PROGRESS)
    assert can_transition(SpecStatus.IN_PROGRESS, SpecStatus.READY)
    assert can_transition(SpecStatus.READY, SpecStatus.APPROVED)
    assert can_transition(SpecStatus.APPROVED, SpecStatus.DRAFT)


def test_lifecycle_rollback_is_only_one_step():
    """O desvio D2 permite UM passo atras, nao volta livre."""
    assert not can_transition(SpecStatus.VERIFYING, SpecStatus.READY)
    assert not can_transition(SpecStatus.IN_PROGRESS, SpecStatus.APPROVED)
    assert not can_transition(SpecStatus.DONE, SpecStatus.VERIFYING)


def test_archived_is_terminal():
    """D2: archived nao tem saida; done so vai para archived."""
    for target in SpecStatus:
        assert not can_transition(SpecStatus.ARCHIVED, target)
    assert can_transition(SpecStatus.DONE, SpecStatus.ARCHIVED)


@settings(max_examples=1000)
@given(st.text(max_size=2000))
def test_parser_never_crashes_unexpectedly(text):
    """Property: arbitrary input either parses or raises SpecParseError.

    max_examples fixado em 1000 porque a success_metric da SPEC-003 promete
    esse numero — o valor vive aqui, nao na prosa da spec (D5).
    """
    with contextlib.suppress(SpecParseError):
        parse_spec(text)
