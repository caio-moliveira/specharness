# ADR-009 — uv workspaces para o monorepo Python

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Cinco packages Python com dependências entre si; contribuidor precisa de setup em um comando.

## Opções consideradas

1. Poetry — maduro, sem workspaces de primeira classe e resolução mais lenta
2. Hatch/PDM — capazes, menor adoção na comunidade-alvo
3. uv workspaces — lockfile único, velocidade, padrão emergente

## Decisão

uv com [tool.uv.workspace] members packages/*; uv.lock único na raiz; uv sync resolve tudo.

## Consequências

Setup em um comando; lock nunca editado à mão (deny no harness).
