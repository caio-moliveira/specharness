# ADR-002 — SQLite default, Postgres opcional, via SQLAlchemy

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Adoção individual exige zero-infra; uso por time exige banco compartilhado que o usuário já opera.

## Opções consideradas

1. Só SQLite — simples, não escala para time
2. Só Postgres — infra obrigatória mata o primeiro contato
3. Ambos via SQLAlchemy — um ORM, dois alvos

## Decisão

SQLite é o default absoluto (zero perguntas); SPECHARNESS_DATABASE_URL troca para Postgres sem mudança de código.

## Consequências

Nenhuma feature exclusiva de Postgres no caminho crítico; migrações Alembic testadas nos dois.
