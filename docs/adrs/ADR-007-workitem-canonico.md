# ADR-007 — Modelo canônico WorkItem no core; adapters traduzem taxonomias

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Redmine (issues/versions), Jira (epics/stories/tasks) e Azure DevOps (features/US/tasks) têm hierarquias incompatíveis. O vínculo Spec↔item precisa ser uniforme.

## Opções consideradas

1. Modelar cada taxonomia nativamente — o core viraria a união de todos os trackers
2. WorkItem canônico + tradução por adapter, extras preservados

## Decisão

O core conhece apenas WorkItem (id, tipo, título, estado, sprint, origem, refs externas, extras). Adapters traduzem nos dois sentidos; campos sem equivalente vão para extras, nunca são descartados.

## Consequências

Brownfield first-class; custo: manutenção dos mapeamentos por adapter.
