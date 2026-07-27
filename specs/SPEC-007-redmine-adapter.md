---
spec: SPEC-007
title: "Adapter Redmine: import e sincronização de WorkItems"
status: verifying
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A3
tracker_refs: []
depends_on: [SPEC-004]
adrs: [ADR-001, ADR-007]
success_metrics:
  - "Import inicial de 500 issues em < 45s respeitando rate limit"
  - "Fidelidade de mapeamento: 100% dos campos canônicos preenchidos ou explicitamente nulos (sem valores inventados)"
  - "Sync incremental captura mudanças de status em < 1 ciclo de polling"
acceptance:
  - Issues e versions do Redmine são importadas como WorkItems canônicos com referência externa estável
  - Mudança de status de spec vinculada atualiza a issue correspondente no Redmine
  - Campos sem equivalente canônico são preservados em extras, nunca descartados silenciosamente
  - Contract tests com cassettes cobrem paginação, auth e campos ausentes
---

## Contexto

Primeiro adapter de tracker (junto ao GitHub Issues) — e o mais relevante para
o caso brownfield de setor público. Traduz a taxonomia do Redmine para o
modelo canônico WorkItem (ADR-007); o core nunca vê tipos do Redmine.

Decisões de modelagem (fechadas no readiness):

- **Versions** viram WorkItems próprios (`kind: version`); além disso, a
  `fixed_version` de cada issue preenche o campo `sprint` do WorkItem dela.
  Assim "issues e versions são importadas" (A1) e as issues ganham sprint.
- **Estado**: o `state` do WorkItem carrega o nome do status nativo do Redmine
  (fidelidade — métrica 2, sem inventar vocabulário). A canonicidade é
  estrutural (um único tipo WorkItem), não um enum fixo de estados.
- **Mapa de status** para o write-back é **configurável** em `specharness.yaml`
  (`tracker.status_map`: status da spec → nome do status no Redmine), porque o
  workflow do Redmine é por instância. Nenhum segredo no arquivo; a API key vem
  só do ambiente (`REDMINE_API_KEY`).
- **Escopo do write-back**: esta spec entrega a *capacidade* de escrita
  (`update_status`); o *gatilho* de ciclo de vida (detectar a spec virando
  `done`) é da orquestração de linking (SPEC-009).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: import e sync de WorkItems do Redmine

  Cenário: import inicial brownfield
    Dado um Redmine conectado com projeto contendo issues e versions
    Quando o import inicial é executado
    Então cada issue e cada version viram WorkItems canônicos com referência externa estável

  Cenário: status flui do specharness para o Redmine
    Dado uma spec vinculada a uma issue do Redmine
    Quando a spec transiciona para "done" com BDD verde
    Então a issue correspondente é atualizada para o status mapeado no Redmine

  Cenário: campo sem equivalente não é perdido
    Dado uma issue com campos customizados do Redmine
    Quando o mapeamento para WorkItem é executado
    Então os campos sem equivalente canônico ficam preservados em extras
```
