---
name: novo-adapter
description: Scaffold completo de um novo adapter do specharness (tracker, git provider ou importer) — porta implementada, contract tests com cassettes, entry point e documentação. Use quando o usuário pedir para criar adapter, integração com Jira/GitLab/Azure DevOps/tracker novo, ou conectar um serviço externo.
---

# novo-adapter

## Regras inegociáveis (ADR-001)

- O adapter implementa uma **porta definida no core** — se a porta não existe,
  PARE e proponha a porta primeiro (é mudança de contrato, exige revisão).
- O adapter NUNCA vaza tipos do serviço externo para fora: converte tudo para
  os modelos canônicos do core (WorkItem etc. — ADR-007).
- Sem contract test passando, o adapter não existe.

## Processo

1. Estrutura em `packages/adapters/src/specharness_adapters/<tipo>/<nome>/`:
   `client.py` (httpx, auth por env var), `adapter.py` (implementa a porta),
   `mapping.py` (tradução para modelos canônicos), `README.md` (escopo do
   token/permissões mínimas + como re-gravar cassettes).
2. Registre o entry point no `pyproject.toml` do package adapters.
3. **Contract tests** com pytest-recording: grave cassettes contra instância
   real (ou sandbox) do serviço; commite as cassettes SEM tokens (confira o
   filtro de headers de auth).
4. Trate explicitamente: paginação, rate limit (retry com backoff), erros de
   auth (mensagem em pt apontando a env var), campos ausentes.
5. Rode `just test` e atualize a matriz de integrações na SPEC-001 §9.
