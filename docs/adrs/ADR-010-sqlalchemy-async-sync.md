# ADR-010 — SQLAlchemy async no server, sync no CLI, models únicos

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

O server é async por natureza (FastAPI); o CLI ganha simplicidade e debugabilidade sendo sync. SQLModel abstrairia demais nosso uso de Alembic.

## Opções consideradas

1. Tudo async — CLI vira cerimônia sem ganho
2. SQLModel — menos boilerplate, menos controle de migração
3. SQLAlchemy 2 puro com engines async e sync sobre os mesmos models

## Decisão

Models declarativos únicos; engine async (aiosqlite/asyncpg) no server, sync no CLI e nos hooks.

## Consequências

Um só lugar para o schema; disciplina para não vazar sessão entre mundos.
