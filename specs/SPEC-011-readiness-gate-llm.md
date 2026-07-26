---
spec: SPEC-011
title: "Readiness Gate: camada LLM (score, issues acionáveis e override auditado)"
status: approved
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A3
tracker_refs: []
depends_on: [SPEC-005, SPEC-010]
adrs: [ADR-006]
success_metrics:
  - "Golden dataset: score dentro da faixa esperada em >= 90% dos casos, em TODOS os modelos suportados (incluindo qwen3:8b local)"
  - "100% das saídas validadas por schema Pydantic (retry automático em falha; 0 parsing de texto livre)"
  - "Custo por avaliação registrado e visível; cache por hash evita reavaliação de spec inalterada"
acceptance:
  - Avaliação produz readiness score 0-100 e issues categorizadas (testabilidade, ambiguidade, contradição, completude), cada uma com sugestão de correção
  - Score abaixo do limiar bloqueia a transição approved -> ready
  - Tech Lead pode sobrepor o gate; o override é registrado com autor, data e justificativa
  - Mudança no prompt do gate exige golden dataset verde no CI (evals/readiness_gate)
  - Spec inalterada não é reavaliada (cache por hash do conteúdo)
---

## Contexto

A camada que justifica o ADR-006: testabilidade, ambiguidade e contradição são
julgamentos semânticos. Score informa, humano decide (override auditado). O
golden dataset em evals/readiness_gate/ é o gate do próprio gate.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: camada LLM do Readiness Gate

  Cenário: spec ambígua recebe score baixo com issues acionáveis
    Dado uma spec cujos cenários permitem duas implementações divergentes
    Quando a avaliação LLM executa
    Então o score fica abaixo do limiar e cada issue traz sugestão de correção

  Cenário: override do Tech Lead é auditado
    Dado uma spec bloqueada pelo gate com score abaixo do limiar
    Quando o Tech Lead aplica override com justificativa
    Então a spec transiciona para ready e o registro guarda autor, data e justificativa

  Cenário: saída fora do schema é recuperada por retry
    Dado uma resposta do modelo que não valida contra o schema Pydantic
    Quando a avaliação processa a resposta
    Então um retry automático é executado antes de reportar falha

  Cenário: spec inalterada usa cache
    Dado uma spec já avaliada e sem mudanças no conteúdo
    Quando o gate é executado novamente
    Então o resultado vem do cache sem nova chamada ao modelo
```
