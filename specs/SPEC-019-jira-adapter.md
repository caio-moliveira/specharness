---
spec: SPEC-019
title: "Adapter Jira: import e sincronização de WorkItems"
status: draft
type: feature
owner: caio
created: 2026-07-28
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-007]
adrs: [ADR-001, ADR-007, ADR-020]
success_metrics:
  - "Import de 300 issues do Jira (epics/stories/tasks) com sprint e labels em < 30s"
  - "0 divergências de estado após ciclo completo import -> mudança -> sync (teste de contrato com cassette)"
  - "100% dos campos Jira sem equivalente canônico preservados em extras (nenhum descarte)"
acceptance:
  - Epics, stories e tasks do Jira são importadas como WorkItems com tipo, estado e sprint mapeados
  - A sprint do agile board do Jira vira a sprint candidata do WorkItem
  - Campos sem equivalente canônico (custom fields, componentes, assignee) são preservados em extras
  - Mudança de status de uma spec escreve de volta apenas o status no Jira, nunca o conteúdo do spec
  - Falha de autenticação produz erro acionável nomeando JIRA_TOKEN
---

## Contexto

Terceiro adapter de tracker, fechando o "next" do roadmap (Jira). Valida o
modelo canônico (ADR-007) contra a taxonomia mais rica que enfrentamos —
epics/stories/tasks + sprints de agile board + custom fields. Reusa a porta
`tracker` (WorkItem/WorkItemStore/StatusWriter da SPEC-007): nenhuma migração
nova, a tabela `work_items` já existe.

Fronteira fixada na ADR-020: o Jira é fonte de verdade do **WorkItem**
(backlog, status, sprint), nunca do conteúdo do **Spec**. O write-back ao Jira
se limita a status (`StatusWriter`), via `status_map` configurável por
instância (cada Jira tem seu próprio workflow). `origin: jira`,
`ref: jira:<tipo>:<key>` (ex.: `jira:story:PROJ-142`).

Decisões de modelagem (a fechar no readiness):

- `JIRA_URL` e `JIRA_TOKEN` vêm do ambiente, nunca do `specharness.yaml`
  (mesma garantia das portas de LLM, repositório e Redmine — só o *nome* da
  env var vive em config).
- `issuetype` do Jira (Epic/Story/Task/Bug) mapeia para o `kind` canônico;
  o `status.name` nativo vira o `state` (fidelidade, sem inventar estado).
- A sprint ativa do agile board vira a sprint candidata; custom fields,
  componentes, assignee e labels são normalizados e preservados em `extras`.

## Fora de escopo

- Sincronizar comentários, anexos ou descrição do issue Jira → conteúdo de spec
  (proibido por ADR-020).
- Criar issues no Jira a partir do specharness (só import + write-back de status).
- Jira Server/Data Center legado; o alvo é Jira Cloud (REST v3).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: import e sync de WorkItems do Jira

  Cenário: import de story com sprint e custom fields
    Dado um projeto Jira com uma story em uma sprint ativa e custom fields preenchidos
    Quando o import é executado
    Então a story vira um WorkItem com tipo, estado e sprint candidata mapeados
    E os custom fields sem equivalente canônico ficam preservados em extras

  Cenário: mudança de status externa reflete no specharness
    Dado um WorkItem vinculado a uma issue Jira em andamento
    Quando o status da issue muda diretamente no Jira
    Então o próximo sync atualiza o estado do WorkItem para o novo status

  Cenário: write-back de status respeita a fronteira da ADR-020
    Dado uma spec que transita para um status com mapeamento em status_map
    Quando o write-back para o Jira é executado
    Então apenas o status da issue é atualizado no Jira

  Cenário: credencial inválida produz erro acionável
    Dado um JIRA_TOKEN inválido
    Quando o import é executado
    Então o erro nomeia a variável JIRA_TOKEN como a credencial a corrigir
```
