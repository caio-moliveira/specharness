# Adapter GitHub (SPEC-006)

Lê pull requests da API REST do GitHub e os entrega como `PullRequest` do core.
Os commits vêm do git local (adapter `git/`, ADR-011); este adapter complementa
com PRs e o vínculo aos commits.

## Token e escopo mínimo

O token é lido **só** da variável de ambiente `GITHUB_TOKEN` — nunca de
`specharness.yaml` nem de qualquer arquivo de config (métrica 3). Escopo mínimo:

- **PAT clássico:** escopo `repo` (leitura de repositórios, inclusive privados).
- **Token fine-grained:** permissão de **leitura** em *Contents* e *Pull requests*
  no(s) repositório(s) alvo.

Uma falha de autenticação (`401`, ou `403` sem cota esgotada) devolve
`AuthenticationFailed` com essa orientação, em português — nunca ecoando o corpo
da resposta (que pode conter o token).

## Testes

Os contract tests são **herméticos**: a callable `fetch` do `GitHubClient` é
injetada, então paginação, rate limit (`403` com `X-RateLimit-Remaining: 0`) e
auth inválida rodam sem rede e sem token (`packages/adapters/tests/test_github_client.py`).
Não há cassettes gravados — o mesmo padrão de I/O injetável do adapter de LLM.
Para exercer a API real, construa `GitHubClient(RepoRef(owner, name), token)` com
um token válido.
