# Adapter GitHub Issues (SPEC-008)

Importa issues de um repositório GitHub como `WorkItem` canônicos (ADR-007),
provando que o modelo funciona para uma segunda taxonomia. Reusa a conexão da
SPEC-006: o repositório vem do remote do git local e a credencial de
`GITHUB_TOKEN`.

## Mapeamento

- **issue** → WorkItem `kind: issue`: `title`→título, `state`
  (`open`/`closed`)→estado (fidelidade), `milestone.title`→sprint candidata.
- **labels** e **assignees** são normalizados (nomes / logins) e guardados em
  `extras`, junto de todo campo sem equivalente canônico — nada é descartado.
- A `ref` estável é `github:issue:<número>`.
- O endpoint `/issues` do GitHub devolve pull requests como issues; itens com a
  chave `pull_request` são ignorados.

## Credencial

Lida **só** de `GITHUB_TOKEN` e enviada como header `Authorization: Bearer` —
nunca gravada em value object nem ecoada em erro. Uma falha de auth (`401`, ou
`403` sem cota) vira `TrackerAuthenticationFailed` citando `GITHUB_TOKEN`.

## Testes

Contract tests **herméticos**: a callable `fetch` do `GitHubIssuesClient` é
injetada, então paginação, auth, rate limit e o filtro de PRs rodam sem rede e
sem token. Há um teste E2E (import → fechamento externo → re-sync) que prova 0
divergências de estado (métrica 2). Sem cassettes — mesmo padrão dos demais
adapters.
