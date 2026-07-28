# Adapter Jira (SPEC-019)

Importa epics, stories e tasks do Jira Cloud (REST v3) como WorkItems
canônicos (ADR-007) e escreve de volta **apenas status** (ADR-020), via
transição de workflow.

## Credenciais e escopo mínimo

- `JIRA_URL` — a URL da instância (ex.: `https://seu-site.atlassian.net`)
- `JIRA_EMAIL` — o e-mail da conta Atlassian
- `JIRA_TOKEN` — API token criado em <https://id.atlassian.com/manage-profile/security/api-tokens>

Auth Basic e-mail+token. Permissões mínimas: *Browse projects* no projeto
importado; para o write-back de status, *Transition issues*. Nada de admin.

O projeto e o mapa de status vivem em `specharness.yaml`:

```yaml
jira:
  project: KAN
  status_map:
    done: Concluído
```

## Como re-gravar as cassettes

Os contract tests leem `packages/adapters/tests/cassettes/jira/*.json`,
gravadas contra uma instância real. Para re-gravar:

```sh
source .env
curl -sS -u "$JIRA_EMAIL:$JIRA_TOKEN" "$JIRA_URL/rest/api/3/field" \
  -o packages/adapters/tests/cassettes/jira/fields.json
curl -sS -u "$JIRA_EMAIL:$JIRA_TOKEN" \
  "$JIRA_URL/rest/api/3/search/jql?jql=project%3DSAM1%20ORDER%20BY%20created%20ASC&fields=*all&maxResults=100" \
  -o packages/adapters/tests/cassettes/jira/search_sam1.json
curl -sS -u "$JIRA_EMAIL:$JIRA_TOKEN" "$JIRA_URL/rest/api/3/issue/SAM1-9/transitions" \
  -o packages/adapters/tests/cassettes/jira/transitions_sam1_9.json
```

Depois de gravar, **sanitize**: nenhum token vai para a cassette (a auth vive
no header, que não é gravado) e e-mails viram `user@example.com`. A instância
usada não tem agile boards com sprint, então os casos de sprint usam payloads
sintéticos no próprio teste, marcados como tal.
