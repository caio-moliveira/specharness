---
spec: SPEC-004
title: "Onboarding: conexão de banco (SQLite default, Postgres opcional)"
status: approved
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-003]
adrs: [ADR-002]
success_metrics:
  - "Setup SQLite: 0 perguntas ao usuário no caminho default (zero-config)"
  - "Troca SQLite -> Postgres sem alteração de código: apenas SPECHARNESS_DATABASE_URL"
  - "Migrações Alembic aplicam do zero em < 10s em ambos os bancos"
acceptance:
  - Sem configuração, o sistema cria e usa SQLite local automaticamente
  - Com SPECHARNESS_DATABASE_URL definida, conecta ao Postgres do usuário
  - Falha de conexão exibe mensagem em português apontando a env var e o problema
  - alembic upgrade head funciona idempotente nos dois bancos
---

## Contexto

Primeira conexão do onboarding (SPEC-001 §5.1). Zero-infra por default é
requisito de adoção; Postgres próprio é requisito de time (ADR-002). Models
únicos SQLAlchemy 2 servem async (server) e sync (CLI) — ADR-010.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: conexão de banco no onboarding

  Cenário: caminho default cria SQLite sem perguntas
    Dado que nenhuma variável de banco está definida
    Quando o usuário executa o primeiro comando que exige persistência
    Então um banco SQLite local é criado e migrado automaticamente

  Cenário: usuário conecta seu próprio Postgres
    Dado que SPECHARNESS_DATABASE_URL aponta para um Postgres acessível
    Quando o onboarding testa a conexão
    Então a conexão é validada e as migrações são aplicadas nesse banco

  Cenário: falha de conexão orienta o usuário
    Dado que SPECHARNESS_DATABASE_URL aponta para um host inacessível
    Quando o onboarding testa a conexão
    Então a mensagem de erro em português indica a env var e a causa provável
```
