# ADR-013 — Tailwind CSS + shadcn/ui no frontend

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Dashboard e wizards precisam de identidade própria sem custo de design system do zero, e sem lock-in de biblioteca de componentes.

## Opções consideradas

1. MUI/Ant — rápido e genérico, difícil descaracterizar, bundle pesado
2. CSS próprio — controle total, custo alto
3. Tailwind + shadcn/ui — componentes copiados para o repo, acessibilidade Radix

## Decisão

shadcn/ui com os componentes versionados no nosso repo; Tailwind para o restante.

## Consequências

Zero lock-in (o código é nosso); controlamos o ritmo de upgrade do Tailwind/React.
