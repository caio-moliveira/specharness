# ADR-015 — justfile como task runner único

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Humanos e agentes de código precisam da MESMA interface de comandos; scripts espalhados divergem.

## Opções consideradas

1. Make — sintaxe hostil, armadilhas de tabs
2. Scripts npm — meio-termo estranho num projeto Python-first
3. justfile — sintaxe limpa, multiplataforma, lista autodocumentada

## Decisão

Todo comando do projeto vive no justfile; AGENTS.md instrui agentes a nunca usar invocações cruas.

## Consequências

Interface única humano↔agente; onboarding de contribuidor = just --list.
