# Contribuindo com o specharness

Obrigado! Este projeto é dogfooding de ponta a ponta: contribuir aqui é usar a
metodologia que o produto implementa.

## Setup (< 10 minutos)

```bash
git clone https://github.com/<org>/specharness && cd specharness
just setup    # uv sync + pre-commit (hooks de lint e de trailer)
just test     # deve terminar verde
```

Requisitos: [uv](https://docs.astral.sh/uv/), git, [just](https://github.com/casey/just).
Python é resolvido pelo uv (`.python-version`). Não precisa de banco nem de
API key para desenvolver o core.

## O fluxo

1. **Toda mudança pertence a uma spec.** Feature nova? Abra issue → vira spec
   em `specs/` (schema na SPEC-001 §7) → depois vira código. Bug? Referencie a
   spec do comportamento esperado.
2. **Branch:** `spec/SPEC-NNN-descricao`. **Commits:** Conventional Commits +
   trailer obrigatório `Spec: SPEC-NNN` no último bloco (o hook bloqueia sem).
3. **Antes do PR:** `just lint && just test`. PRs que tocam prompts de LLM
   exigem golden dataset atualizado em `evals/`.
4. **Decisão de arquitetura no meio do caminho?** Registre ADR em `docs/adrs/`
   (template no índice) — decisões sem alternativas consideradas são
   devolvidas.

## Onde contribuir

| Nível | Onde | O quê |
|---|---|---|
| Primeiro contato | `profiles/` | Práticas de vendor mudaram → PR com fonte citada |
| Confortável | `packages/adapters/` | Novo tracker/importer (contract test obrigatório) |
| Avançado | `packages/core/` | Domínio (pyright strict, cobertura ≥85%) |

## Fronteiras invioláveis

- `core` não faz I/O nem importa framework (ADR-001)
- Métricas nunca expõem indivíduos (ADR-008) — PRs nessa direção são fechados
  com referência ao ADR, sem exceções
- `profiles/` só aceita prática com fonte oficial citada (ADR-004)

## Dúvidas

GitHub Discussions. Em português ou inglês — ambos bem-vindos.
