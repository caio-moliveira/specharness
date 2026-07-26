# ADR-012 — pytest-bdd para o nosso gate BDD

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Nossos próprios cenários precisam rodar como gate. Já temos pytest para unit e contract tests.

## Opções consideradas

1. behave — runner separado, fixtures duplicadas
2. pytest-bdd — mesmos fixtures, um runner só

## Decisão

pytest-bdd integra os cenários das nossas specs na suíte pytest existente.

## Consequências

Um comando (just test) cobre tudo; step definitions vivem junto dos testes.
