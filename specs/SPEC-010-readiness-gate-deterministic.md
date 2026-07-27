---
spec: SPEC-010
title: "Readiness Gate: camada determinística (Definition of Ready automatizada)"
status: in_progress
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
passaram aqui. Usa o parser da SPEC-003.

Decisões (fechadas no readiness):

- O Gherkin do subconjunto que autoramos é parseado por um **parser puro
  interno no core** (`gherkin.py`), na mesma filosofia do `trailers.py` — sem
  dependência externa para uma gramática controlada. (A menção a
  gherkin-official no plano original foi substituída por essa escolha.)
- A "matriz critério × cenário" mecânica usa **overlap de palavras-chave de
  conteúdo** (fora stopwords/keywords). É um piso: um critério sem nenhum termo
  em comum com algum cenário é bloqueado; a cobertura semântica fina fica para a
  camada LLM (SPEC-011). Calibrado para 0 falso-positivos em specs boas.
- "Não-mensurável sintaticamente": métrica sem número, unidade ou comparador.
  success_metrics vazio (ou nenhuma mensurável) bloqueia; métricas individuais
  não-mensuráveis viram recomendação.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: camada determinística do Readiness Gate

  Cenário: spec completa passa no piso
    Dado uma spec com critérios, cenários que os cobrem e métricas mensuráveis
    Quando o gate determinístico executa
    Então o resultado é aprovado sem bloqueadores

  Cenário: spec sem critérios ou sem cenários não passa
    Dado uma spec sem critérios de aceite ou sem cenários Gherkin parseáveis
    Quando o gate determinístico executa
    Então o resultado tem um bloqueador e não passa

  Cenário: critério sem cenário é bloqueador com localização
    Dado uma spec cujo segundo critério de aceite não tem cenário correspondente
    Quando o gate determinístico executa
    Então o bloqueador aponta o critério descoberto na matriz critério x cenário

  Cenário: métrica não-mensurável é reportada
    Dado uma spec com uma success_metric sem número, unidade ou comparador
    Quando o gate determinístico executa
    Então a métrica não-mensurável é reportada com sua localização

  Cenário: termo ambíguo é detectado pelo lint
    Dado um cenário contendo o termo "rápido" em um Então
    Quando o gate determinístico executa
    Então o lint reporta o termo ambíguo com sugestão de torná-lo mensurável

  Cenário: dependência archived bloqueia
    Dado uma spec cujo depends_on referencia uma spec archived
    Quando o gate determinístico executa
    Então o bloqueador indica a dependência congelada
```
