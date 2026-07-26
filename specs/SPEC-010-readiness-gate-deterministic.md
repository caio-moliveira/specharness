---
spec: SPEC-010
title: "Readiness Gate: camada determinística (Definition of Ready automatizada)"
status: approved
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A2
tracker_refs: []
depends_on: [SPEC-003]
adrs: [ADR-006]
success_metrics:
  - "Execução do gate determinístico em < 500ms por spec"
  - "0 falso-positivos na suite de fixtures (specs boas nunca são bloqueadas por check mecânico)"
  - "Lint de BDD detecta 100% dos termos ambíguos da lista canônica em fixtures"
acceptance:
  - Spec sem critérios de aceite ou sem cenários Gherkin parseáveis não passa
  - Critério de aceite sem cenário que o cubra é reportado com a matriz critério x cenário
  - success_metrics ausentes ou não-mensuráveis sintaticamente são reportadas
  - depends_on com spec inexistente ou archived bloqueia
  - Lint de BDD aplica um Quando por cenário e sinaliza termos ambíguos da lista canônica
  - Saída é estruturada em bloqueadores e recomendações, cada um com localização
---

## Contexto

O piso do gate (SPEC-001 §8.1): tudo que é mecanicamente verificável roda
sempre, rápido e sem custo. A camada LLM (SPEC-011) só recebe specs que já
passaram aqui. Usa o parser da SPEC-003 e o AST do gherkin-official.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: camada determinística do Readiness Gate

  Cenário: spec completa passa no piso
    Dado uma spec com critérios, cenários que os cobrem e métricas mensuráveis
    Quando o gate determinístico executa
    Então o resultado é aprovado sem bloqueadores

  Cenário: critério sem cenário é bloqueador com localização
    Dado uma spec cujo segundo critério de aceite não tem cenário correspondente
    Quando o gate determinístico executa
    Então o bloqueador aponta o critério descoberto na matriz critério x cenário

  Cenário: termo ambíguo é detectado pelo lint
    Dado um cenário contendo o termo "rápido" em um Então
    Quando o gate determinístico executa
    Então o lint reporta o termo ambíguo com sugestão de torná-lo mensurável

  Cenário: dependência archived bloqueia
    Dado uma spec cujo depends_on referencia uma spec archived
    Quando o gate determinístico executa
    Então o bloqueador indica a dependência congelada
```
