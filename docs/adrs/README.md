# Registro de Decisões de Arquitetura (ADRs)

Toda decisão relevante vive aqui. Nunca edite o conteúdo histórico de um ADR —
registre um novo que o substitua (skill `registrar-adr`).

| ADR | Decisão | Status |
|---|---|---|
| [ADR-001](ADR-001-formato-canonico-ports-adapters.md) | Formato canônico primeiro, adapters depois (ports & adapters) | aceita |
| [ADR-002](ADR-002-sqlite-default-postgres-opcional.md) | SQLite default, Postgres opcional, via SQLAlchemy | aceita |
| [ADR-003](ADR-003-agentsmd-base-harness.md) | AGENTS.md como base do harness + camada por runtime | aceita |
| [ADR-004](ADR-004-harness-profiles-como-dados.md) | Harness profiles como dados versionados, não código | aceita |
| [ADR-005](ADR-005-litellm-sob-porta-propria.md) | LiteLLM sob interface própria LLMClient | aceita |
| [ADR-006](ADR-006-llm-obrigatoria-gate-llm-first.md) | Conexão LLM obrigatória; gate de qualidade é LLM-first | aceita |
| [ADR-007](ADR-007-workitem-canonico.md) | Modelo canônico WorkItem no core; adapters traduzem taxonomias | aceita |
| [ADR-008](ADR-008-anti-vigilancia.md) | Métricas medem processo/spec/agente — nunca o indivíduo | aceita |
| [ADR-009](ADR-009-uv-workspaces.md) | uv workspaces para o monorepo Python | aceita |
| [ADR-010](ADR-010-sqlalchemy-async-sync.md) | SQLAlchemy async no server, sync no CLI, models únicos | aceita |
| [ADR-011](ADR-011-git-cli-wrapper.md) | Git via wrapper fino sobre o CLI | aceita |
| [ADR-012](ADR-012-pytest-bdd.md) | pytest-bdd para o nosso gate BDD | substituída por ADR-018 |
| [ADR-013](ADR-013-tailwind-shadcn.md) | Tailwind CSS + shadcn/ui no frontend | aceita |
| [ADR-014](ADR-014-openapi-codegen.md) | Cliente TypeScript gerado do OpenAPI (hey-api) | aceita |
| [ADR-015](ADR-015-justfile-task-runner.md) | justfile como task runner único | aceita |
| [ADR-016](ADR-016-separacao-implementacao-verificacao.md) | Quem implementa não arbitra: separação implementação/verificação | aceita |
| [ADR-017](ADR-017-identidade-visual.md) | Identidade visual "Gate & Evidence" | aceita |
| [ADR-018](ADR-018-runner-bdd-interno.md) | Runner de BDD interno mínimo, não pytest-bdd, para o verify | aceita |
| [ADR-019](ADR-019-modo-demo-dashboard.md) | Modo demo do dashboard: banco dedicado, rótulo DEMO e origem declarada | aceita |
| [ADR-020](ADR-020-fronteira-workitem-tracker-spec-repo.md) | Fronteira WorkItem-no-tracker / Spec-no-repo; comunidade no GitHub Projects, Jira como adapter | aceita |
