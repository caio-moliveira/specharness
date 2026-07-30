---
spec: SPEC-033
title: "ready: veredito PRONTA grava a transição para status ready"
status: verifying
type: feature
owner: caio
created: 2026-07-30
updated: 2026-07-30
sprint: 2026-C2
depends_on: [SPEC-010, SPEC-011, SPEC-013, SPEC-017]
adrs: [ADR-016]
success_metrics:
  - "100% dos caminhos de promoção cobertos por teste de CLI: approved+PRONTA grava, override grava, draft+PRONTA não grava e orienta, BLOQUEADA não toca o arquivo — 1 teste por caminho"
  - "Transição gravada é visível ao StatusHistoryReader (cycle time coletável) — 1 teste de integração com git real"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "Veredito PRONTA sobre spec em status approved grava status: ready (e updated) no arquivo da spec"
  - "Veredito PRONTA via override auditado também grava a transição"
  - "Veredito PRONTA sobre spec em draft não grava e orienta a aprovar primeiro (draft -> approved é decisão humana)"
  - "Veredito BLOQUEADA nunca modifica o arquivo da spec"
  - "A promoção é anunciada na saída (e refletida no payload do --json)"
---

## Contexto

A métrica-tese do produto — cycle time `ready → done` — é computada pelas
transições de status no histórico git do arquivo da spec
(`StatusHistoryReader`). A validação de M1 (2026-07-30) fechou 7 specs em
`done` e nenhuma tem cycle time: o fluxo real nunca grava `status: ready`,
porque o `ready` apenas emite o veredito e ninguém edita o arquivo. O gate
aprova, mas a aprovação não vira fato no registro — e a correlação
readiness × sobrevivência, propósito declarado do produto, fica sem o eixo x.

## Fora de escopo

- Promover `draft → approved` automaticamente (aprovação de conteúdo é humana).
- Promover além de `ready` (`in_progress` em diante pertence à implementação).
- Mudar o cálculo do cycle time ou o `StatusHistoryReader`.
- Commitar a mudança pelo CLI (gravar no arquivo basta; o commit é do fluxo).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: veredito PRONTA vira transição de status registrada

  Cenário: aprovação nas duas camadas grava ready
    Dado uma spec em status approved que passa no piso determinístico e na camada LLM
    Quando o ready roda sobre ela
    Então o arquivo da spec passa a ter status ready e a promoção é anunciada na saída

  Cenário: override auditado grava ready
    Dado uma spec em status approved e um override com autor e justificativa
    Quando o ready roda com a opção de override
    Então o arquivo da spec passa a ter status ready

  Cenário: draft aprovado não é promovido
    Dado uma spec em status draft que passa nas duas camadas
    Quando o ready roda sobre ela
    Então o arquivo permanece em draft e a saída orienta a aprovar a spec primeiro

  Cenário: bloqueio não toca o arquivo
    Dado uma spec em status approved que reprova no piso determinístico
    Quando o ready roda sobre ela
    Então o arquivo da spec permanece exatamente como estava

  Cenário: a transição gravada alimenta o cycle time
    Dado uma spec promovida a ready pelo veredito e depois marcada done pelo CI
    Quando as transições da spec são lidas do histórico git
    Então o cycle time entre ready e done é computável
```

## Notas de implementação

- Só CLI (`ready` em `packages/cli/src/specharness_cli/main.py`): nos caminhos
  que terminam em `ok=True` (aprovada nas duas camadas; override), se o status
  atual é `approved`, regravar o frontmatter com `status: ready` e `updated:`
  do dia — via substituição textual da linha (preserva formatação do arquivo,
  como o restante do repo faz). `can_transition(APPROVED, READY)` já autoriza;
  o hook de schema aceita (não é `done`).
- Em `draft`, imprimir orientação ("aprove a spec primeiro: status approved")
  sem tocar o arquivo. Em `--json`, campo `promoted: true|false`.
- Teste de integração do cenário 5: repo git temporário com dois commits
  (ready gravado pelo comando; done editado à mão) e `StatusHistoryReader` +
  `cycle_time_seconds` sobre ele.
