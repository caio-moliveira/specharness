---
spec: SPEC-019
title: "Adapter Jira: import e sincronização de WorkItems"
status: approved
type: feature
owner: caio
created: 2026-07-28
updated: 2026-07-28
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-007]
adrs: [ADR-001, ADR-007, ADR-020]
success_metrics:
  - "Import de 300 issues do Jira (epics/stories/tasks) com sprint e labels em < 30s"
  - "0 divergências de estado após ciclo completo import -> mudança -> sync (teste de contrato com cassette)"
  - "100% dos campos Jira sem equivalente canônico preservados em extras (nenhum descarte)"
acceptance:
  - Epics, stories e tasks do Jira são importadas como WorkItems com tipo, estado e sprint mapeados conforme as tabelas desta spec
  - A sprint ativa do issue vira a sprint candidata do WorkItem; issue sem sprint gera WorkItem com sprint nula
  - Campos sem equivalente canônico (custom fields, componentes, labels, assignee como veio no payload) são preservados em extras
  - Mudança de status de uma spec escreve de volta apenas o status no Jira, nunca summary ou description
  - Falha de autenticação produz erro acionável nomeando JIRA_TOKEN; falha de rede produz erro acionável sem persistir import parcial
---

## Contexto

Terceiro adapter de tracker, fechando o "next" do roadmap (Jira). Valida o
modelo canônico (ADR-007) contra a taxonomia mais rica que enfrentamos —
epics/stories/tasks + sprints de agile board + custom fields. Reusa a porta
`tracker` (WorkItem/WorkItemStore/StatusWriter da SPEC-007): nenhuma migração
nova, a tabela `work_items` já existe.

Fronteira fixada na ADR-020: o Jira é fonte de verdade do **WorkItem**
(backlog, status, sprint), nunca do conteúdo do **Spec**. O write-back ao Jira
se limita a status (`StatusWriter`). `origin: jira`,
`ref: jira:<tipo>:<key>` (ex.: `jira:story:PROJ-142`).

## Decisões de modelagem

**Credenciais.** `JIRA_URL`, `JIRA_EMAIL` e `JIRA_TOKEN` vêm do ambiente,
nunca do `specharness.yaml` (mesma garantia das portas de LLM, repositório e
Redmine — só o *nome* da env var vive em config). Auth Basic e-mail+token
(Jira Cloud, REST v3).

**Mapeamento de tipo.** `issuetype.name` → `kind` canônico, caso-insensível:

| issuetype Jira | kind canônico |
|---|---|
| Epic | `epic` |
| Story | `story` |
| Task | `task` |
| Bug | `bug` |
| Sub-task | `subtask` |
| qualquer outro | nome nativo em minúsculas (fidelidade, sem inventar) |

**Estado: import e write-back são fluxos independentes.**

- No **import**, `state` = `status.name` bruto do Jira (string livre,
  fidelidade sem normalização). O `status_map` não participa do import.
- No **write-back**, o `status_map` do `specharness.yaml` converte o status
  canônico da spec no nome de status do Jira daquela instância (cada Jira tem
  seu próprio workflow); a transição correspondente é resolvida via API de
  transitions. Status de spec sem entrada no `status_map` não gera write-back.

**Sprint.** A sprint candidata é o campo sprint do próprio payload do issue:
a primeira sprint com `state == "active"`; sem sprint ativa, a de maior id
com `state == "future"`; sem nenhuma, `sprint = null` (backlog puro).

**Extras.** Mapa raso (flat) `nome do campo Jira → valor JSON como veio no
payload`. Entram: custom fields preenchidos, `components`, `labels`,
`assignee`. O assignee é preservado como o objeto que o payload do issue já
traz (`accountId` + `displayName`), sem chamada extra de resolução de usuário
— se o payload não traz assignee, a chave é omitida. Campos com valor `null`
ou vazio são omitidos (nada a preservar). Nenhum campo preenchido é
descartado.

**Sync.** O gatilho é sempre o comando `specharness connect jira` (polling
explícito, como nos adapters de Redmine e GitHub Issues). Sem webhooks nesta
fase. O import é idempotente: a chave de identidade é o `ref`
(`jira:<tipo>:<key>`) — um WorkItem com o mesmo `ref` é atualizado, nunca
duplicado; re-executar sem mudanças no Jira é no-op.

**Falha de rede.** Timeout ou queda de conexão durante o import interrompe a
execução com erro acionável em português e não persiste nada daquela execução
(o sync no store é atômico por execução); os WorkItems de execuções
anteriores permanecem intactos.

## Fora de escopo

- Sincronizar comentários, anexos ou descrição do issue Jira → conteúdo de spec
  (proibido por ADR-020).
- Criar issues no Jira a partir do specharness (só import + write-back de status).
- Resolução de usuário via API (`/user` do Jira) para enriquecer assignee.
- Webhooks de transição; o sync é por comando explícito.
- Jira Server/Data Center legado; o alvo é Jira Cloud (REST v3).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: import e sync de WorkItems do Jira

  Cenário: import de story com sprint ativa e custom fields
    Dado um projeto Jira com uma story em uma sprint ativa e custom fields preenchidos
    Quando o comando de import é executado
    Então a story vira um WorkItem com kind "story", state igual ao status.name do Jira e a sprint ativa como sprint candidata
    E os custom fields preenchidos ficam preservados em extras com o nome do campo Jira como chave

  Cenário: issue de backlog sem sprint
    Dado uma task do Jira que não pertence a nenhuma sprint
    Quando o comando de import é executado
    Então a task vira um WorkItem com sprint nula e os demais campos mapeados

  Cenário: mudança de status externa reflete no specharness
    Dado um WorkItem vinculado a uma issue Jira em andamento
    Quando o comando de import é executado de novo após o status da issue mudar no Jira
    Então o estado do WorkItem é atualizado para o novo status.name e nenhum item é duplicado

  Cenário: write-back de status respeita a fronteira da ADR-020
    Dado uma spec que transita para um status com mapeamento em status_map
    Quando o write-back para o Jira é executado
    Então apenas o status da issue é atualizado no Jira
    E o summary e a description da issue permanecem inalterados no Jira

  Cenário: credencial inválida produz erro acionável
    Dado um JIRA_TOKEN inválido
    Quando o comando de import é executado
    Então o erro em português nomeia a variável JIRA_TOKEN como a credencial a corrigir

  Cenário: falha de rede não persiste import parcial
    Dado que o Jira para de responder no meio do import
    Quando o comando de import é executado
    Então o erro em português orienta a verificar a rede e tentar de novo
    E nenhum WorkItem daquela execução é persistido
```
