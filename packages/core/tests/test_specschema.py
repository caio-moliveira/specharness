"""Tests for the spec parser — the central contract (SPEC-003)."""

import contextlib
from datetime import date

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from specharness_core import (
    SpecParseError,
    SpecStatus,
    SpecType,
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
created: 2026-01-15
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


MIXED_FENCES_SPEC = """\
---
spec: SPEC-044
title: "Spec com cercas mistas"
---

## Contexto

```python
CONSTANTE = "cerca de python, nao e cenario"
```

```
cerca nua sem rotulo de linguagem
```

```gherkin
Funcionalidade: unica
  Cenario: um
    Quando algo acontece
    Entao algo e verificado
```

```yaml
chave: valor de configuracao
```
"""


def test_parses_valid_spec():
    parsed = parse_spec(VALID_SPEC)
    assert parsed.spec_id == "SPEC-042"
    assert parsed.frontmatter.status is SpecStatus.READY
    assert parsed.frontmatter.success_metrics == ["Latencia p95 < 800ms"]
    assert parsed.frontmatter.depends_on == ["SPEC-001"]
    # `created` e a unica coercao nao trivial do schema: str YAML -> date.
    assert parsed.frontmatter.created == date(2026, 1, 15)
    assert parsed.frontmatter.type is SpecType.FEATURE
    assert parsed.frontmatter.acceptance == ["Busca retorna resultados com o termo destacado"]
    assert "## Contexto" in parsed.body


def test_body_excludes_frontmatter():
    """O corpo alimenta o Readiness Gate: o frontmatter nao pode vazar nele."""
    parsed = parse_spec(VALID_SPEC)
    assert not parsed.body.lstrip().startswith("---")
    assert "spec: SPEC-042" not in parsed.body
    assert "Latencia p95" not in parsed.body


def test_rejects_frontmatter_missing_required_fields():
    """D1: `spec` e `title` sao os unicos obrigatorios — e sao mesmo.

    A metade oposta de D1 (o resto e opcional, com defaults declarados) e
    provada por test_optional_fields_have_declared_defaults.
    """
    with pytest.raises(SpecParseError, match="Field required") as sem_title:
        parse_spec("---\nspec: SPEC-042\n---\n\nCorpo.\n")
    assert "title" in str(sem_title.value)

    with pytest.raises(SpecParseError, match="Field required") as sem_spec:
        parse_spec('---\ntitle: "Sem id"\n---\n\nCorpo.\n')
    assert "spec" in str(sem_spec.value)


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


def test_gherkin_blocks_ignores_other_fenced_languages():
    """O rotulo `gherkin` tem de importar.

    Os specs reais deste repo tem muito mais cerca do que cenario (SPEC-001:
    8 cercas, 1 gherkin). Um parser que devolvesse toda cerca entregaria lixo
    ao Readiness Gate.
    """
    blocks = parse_spec(MIXED_FENCES_SPEC).gherkin_blocks
    assert len(blocks) == 1
    assert "Funcionalidade: unica" in blocks[0]
    joined = "\n".join(blocks)
    assert "CONSTANTE" not in joined
    assert "cerca nua" not in joined
    assert "valor de configuracao" not in joined


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


@pytest.mark.parametrize(
    "bad_id",
    [
        "SPEC42",  # sem hifen
        "SPEC-42",  # dois digitos
        "SPEC-042junk",  # sufixo
        "veja SPEC-042 aqui",  # id embutido em texto
        "spec-042",  # minusculas
        "SPEC-",  # sem digitos
    ],
)
def test_rejects_ids_outside_the_pattern(bad_id):
    """Um negativo so (SPEC42) passava em regex frouxa; estes fecham as bordas."""
    doc = VALID_SPEC.replace("spec: SPEC-042", f'spec: "{bad_id}"')
    with pytest.raises(SpecParseError, match="invalid spec id"):
        parse_spec(doc)


@pytest.mark.parametrize("bad_dep", ["SPEC-42", "SPEC-042junk", "spec-042", "nonsense"])
def test_rejects_dependency_ids_outside_the_pattern(bad_dep):
    doc = VALID_SPEC.replace("depends_on: [SPEC-001]", f'depends_on: ["{bad_dep}"]')
    with pytest.raises(SpecParseError, match="depends_on"):
        parse_spec(doc)


def test_optional_fields_have_declared_defaults():
    """D1: o resto e opcional — e com ESTES defaults, nao com quaisquer.

    Um default `status: done` derrotaria em silencio a regra "transicao para
    done e exclusiva do CI" do hook de schema (ADR-016).
    """
    fm = parse_spec('---\nspec: SPEC-045\ntitle: "Minima"\n---\n\nCorpo.\n').frontmatter
    assert fm.status is SpecStatus.DRAFT
    assert fm.type is SpecType.FEATURE
    assert fm.owner is None
    assert fm.created is None
    assert fm.tracker_refs == []
    assert fm.depends_on == []
    assert fm.adrs == []
    assert fm.success_metrics == []
    assert fm.acceptance == []


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


#: Tabela esperada do ciclo de vida, declarada AQUI de propósito: importar
#: ALLOWED_TRANSITIONS do módulo faria o teste concordar com qualquer
#: alteração da implementação, provando nada. SPEC-001 §7.2 + desvio D2.
EXPECTED_TRANSITIONS: dict[SpecStatus, set[SpecStatus]] = {
    SpecStatus.DRAFT: {SpecStatus.APPROVED},
    SpecStatus.APPROVED: {SpecStatus.READY, SpecStatus.DRAFT},
    SpecStatus.READY: {SpecStatus.IN_PROGRESS, SpecStatus.APPROVED},
    SpecStatus.IN_PROGRESS: {SpecStatus.VERIFYING, SpecStatus.READY},
    SpecStatus.VERIFYING: {SpecStatus.DONE, SpecStatus.IN_PROGRESS},
    SpecStatus.DONE: {SpecStatus.ARCHIVED},
    SpecStatus.ARCHIVED: set(),
}


def test_lifecycle_transition_table_is_exhaustive():
    """Todos os 7x7 pares, não só os que alguém lembrou de escrever."""
    for current in SpecStatus:
        for target in SpecStatus:
            expected = target in EXPECTED_TRANSITIONS[current]
            assert can_transition(current, target) is expected, (
                f"{current.value} -> {target.value}: esperado {expected}"
            )


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
    # Conjunto, nao um assert solto: "so vai para archived" exige provar que
    # nenhum outro destino a partir de done esta aberto.
    reachable_from_done = {t for t in SpecStatus if can_transition(SpecStatus.DONE, t)}
    assert reachable_from_done == {SpecStatus.ARCHIVED}


@settings(max_examples=1000)
@given(st.text(max_size=2000))
def test_parser_never_crashes_unexpectedly(text):
    """Property: arbitrary input either parses or raises SpecParseError.

    max_examples fixado em 1000 porque a success_metric da SPEC-003 promete
    esse numero — o valor vive aqui, nao na prosa da spec (D5).
    """
    with contextlib.suppress(SpecParseError):
        parse_spec(text)
