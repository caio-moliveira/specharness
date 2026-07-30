---
spec: SPEC-009
title: "track: linking commit->spec via trailer e detecção de órfãos"
status: done
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A2
tracker_refs: []
depends_on: [SPEC-003, SPEC-006]
adrs: [ADR-011]
success_metrics:
  - "Precisão do linking: 100% dos trailers válidos vinculados (0 falso-negativo em suite de fixtures)"
  - "Paridade com git: parser interno e git interpret-trailers concordam em 100% da suite de equivalência"
  - "Specs órfãs e commits órfãos calculados a cada sync (janela <= 1 ciclo)"
acceptance:
  - Commit com trailer válido é vinculado à spec e o vínculo aparece na visão pipeline
  - Commit com trailer para spec inexistente é sinalizado como inválido, não ignorado
  - Commits sem trailer entram na métrica de commits órfãos
  - Specs in_progress sem nenhum commit vinculado entram na métrica de specs órfãs
  - Múltiplos trailers no mesmo commit geram múltiplos vínculos
---

## Contexto

O elo da cadeia WorkItem ↔ Spec ↔ Commit (SPEC-001 §6). O trailer é a fonte
de verdade (§7.3); órfãos são métrica de higiene, não erro fatal. A suite de
equivalência com git interpret-trailers pina o comportamento (ADR-011).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: linking de commits a specs

  Cenário: trailer válido cria o vínculo
    Dado um commit cuja mensagem termina com o trailer "Spec: SPEC-042"
    Quando o track processa o commit
    Então o commit fica vinculado à SPEC-042 na visão pipeline

  Cenário: trailer para spec inexistente é sinalizado
    Dado um commit com trailer "Spec: SPEC-999" e nenhuma spec com esse id
    Quando o track processa o commit
    Então o commit é marcado com vínculo inválido e aparece no relatório de higiene

  Cenário: commit sem trailer vira métrica de órfão
    Dado um commit sem nenhum trailer "Spec:"
    Quando o track processa o commit
    Então o commit entra na contagem de commits órfãos da sprint

  Cenário: spec in_progress sem commit vira métrica de órfã
    Dado uma spec in_progress sem nenhum commit vinculado
    Quando o track é executado
    Então a spec entra na contagem de specs órfãs

  Cenário: múltiplos trailers geram múltiplos vínculos
    Dado um commit com trailers "Spec: SPEC-010" e "Spec: SPEC-011"
    Quando o track processa o commit
    Então o commit fica vinculado às duas specs
```

## Notas de implementação

O linking é **decisão pura no core** (`link_commits`): recebe os commits (com os
trailers `Spec:` já extraídos na ingestão da SPEC-006) e o registro de specs do
disco (SPEC-003), e devolve vínculos válidos/inválidos, commits órfãos e specs
órfãs — sem I/O, sem tabela nova (calculado a cada `track`, métrica 3). Um trailer
mal-formado ou para spec inexistente vira vínculo inválido (sinalizado, nunca
descartado). A paridade com `git interpret-trailers` (ADR-011, métrica 2) é
pinada por uma suíte de equivalência. "Commits órfãos da sprint" é contado
globalmente — um commit sem trailer não pertence a uma sprint.
