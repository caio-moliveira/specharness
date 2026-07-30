# Contribuindo com o specharness

Obrigado! Este projeto é dogfooding de ponta a ponta: contribuir aqui é usar a
metodologia que o produto implementa.

## Setup (< 10 minutos)

```bash
git clone https://github.com/caio-moliveira/specharness && cd specharness
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

## `done` é do CI — proteja a main (mantenedores)

A transição `verifying → done` é arbitrada pelos checks do PR (`verify-bdd`,
`validate`, `test` — ADR-016). Um merge antes dos checks terminarem fura o
árbitro: o workflow re-roda no push para a `main`, mas aí o merge já aconteceu.
Configure **branch protection** na `main` (Settings → Branches → Add rule):

- *Require status checks to pass before merging*, marcando `verify-bdd`,
  `validate`, `lint` e `test` como obrigatórios;
- *Require branches to be up to date before merging*.

Com isso, nenhum `done` — nem nenhuma regressão — entra sem o veredito verde.

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
