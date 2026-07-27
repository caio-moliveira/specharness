# Adapter Redmine (SPEC-007)

Importa issues e versions de um projeto Redmine como `WorkItem` canônicos
(ADR-007) e escreve o status de volta. O core nunca vê tipos do Redmine.

## Config e credencial

A URL e o projeto ficam em `specharness.yaml` (seção `tracker`) — **sem
segredo**. A credencial é lida **só** da variável de ambiente `REDMINE_API_KEY`
e enviada no header `X-Redmine-API-Key`, nunca gravada em value object nem ecoada
em erro.

```yaml
tracker:
  url: https://redmine.exemplo.gov.br
  project: meu-projeto
  # Mapa spec-status -> nome do status no Redmine (write-back). O workflow do
  # Redmine é por instância, então isto é configurável, não hardcoded.
  status_map:
    done: Fechada
    in_progress: Em andamento
```

## Mapeamento (fidelidade — métrica 2)

- **issue** → WorkItem `kind: issue`: `subject`→título, `status.name`→estado,
  `fixed_version.name`→sprint. Todo campo sem equivalente (descrição, prioridade,
  autor, `custom_fields`, datas…) é preservado em `extras`, nunca descartado.
- **version** → WorkItem `kind: version`: `name`→título, `status`→estado.
- A `ref` estável é `redmine:<kind>:<id>` — imune a colisão de id entre issue e
  version, e estável entre syncs.

## Rate limit e paginação (métrica 1)

Paginação por `offset`/`limit` até `total_count`. Um `429` é reprocessado após
backoff (respeitando `Retry-After`) e só vira `TrackerRateLimited` se persistir.

## Testes

Contract tests **herméticos**: a callable `fetch` do `RedmineClient` é injetada,
então paginação, auth, rate limit e campos ausentes rodam sem rede e sem key
(`packages/adapters/tests/test_redmine_client.py`). O `sleep` do backoff também é
injetável. Não há cassettes gravados — mesmo padrão dos adapters de LLM e GitHub.
