# ADR-011 — Git via wrapper fino sobre o CLI

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Precisamos de interpret-trailers, log estruturado e blame — com comportamento idêntico ao ambiente do usuário e zero dependência binária.

## Opções consideradas

1. pygit2 — rápido, arrasta libgit2 (dor de instalação)
2. GitPython — API conveniente que shells out de qualquer forma
3. Wrapper próprio sobre o git CLI — dependência universal, semântica canônica

## Decisão

Subprocess disciplinado sobre git (interpret-trailers, log --format, blame), com parser interno puro espelhando trailers para hooks/testes e suite de equivalência pinando a paridade.

## Consequências

Zero deps nativas; requisito: git presente (universal no público-alvo).
