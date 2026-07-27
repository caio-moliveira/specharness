---
spec: SPEC-008
title: "Adapter GitHub Issues: import e sincronização de WorkItems"
status: ready
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A3
tracker_refs: []
depends_on: [SPEC-006]
adrs: [ADR-001, ADR-007]
success_metrics:
  - "Import de 300 issues com labels e milestones em < 30s"
  - "0 divergências de estado após ciclo completo import -> mudança -> sync (teste E2E)"
acceptance:
  - Issues são importadas como WorkItems com labels, milestone e assignees mapeados
  - Milestones são mapeados para sprints candidatas
  - Fechamento de issue no GitHub reflete no WorkItem no próximo sync
---

## Contexto

Segundo adapter de tracker, deliberadamente simples: valida que o modelo
canônico (ADR-007) funciona para taxonomias distintas antes de encarar
Jira e Azure DevOps na Fase C. Reusa a conexão da SPEC-006.

Decisões de modelagem (fechadas no readiness):

- Reusa a porta `tracker` (WorkItem/WorkItemStore, da SPEC-007) e a conexão
  GitHub (RepoRef do remote local + GITHUB_TOKEN, da SPEC-006). `origin: github`,
  `ref: github:issue:<número>`. Nenhuma migração nova — a tabela `work_items` já
  existe.
- `state` do GitHub (`open`/`closed`) vira o estado (fidelidade); `milestone`
  vira a sprint candidata; **labels e assignees** são normalizados e preservados
  em `extras`, junto de todo campo sem equivalente (ADR-007).
- O endpoint `/issues` do GitHub devolve pull requests como issues; itens com a
  chave `pull_request` são ignorados.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: import e sync de WorkItems do GitHub Issues

  Cenário: import com labels e milestone
    Dado um repositório com issues rotuladas e milestone definida
    Quando o import é executado
    Então cada issue vira WorkItem com labels, assignees e sprint candidata mapeados

  Cenário: fechamento externo reflete no specharness
    Dado um WorkItem vinculado a uma issue aberta
    Quando a issue é fechada diretamente no GitHub
    Então o próximo sync atualiza o estado do WorkItem para fechado
```
