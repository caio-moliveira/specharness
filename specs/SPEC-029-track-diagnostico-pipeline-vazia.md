---
spec: SPEC-029
title: "CLI: track distingue pipeline vazia de pipeline limpa"
status: verifying
type: feature
owner: caio
created: 2026-07-30
updated: 2026-07-30
sprint: 2026-C2
depends_on: [SPEC-006, SPEC-009, SPEC-017]
adrs: [ADR-016]
success_metrics:
  - "100% dos caminhos de saída do track com zero commits ingeridos terminam com a orientação 'specharness connect repo' — 1 teste de CLI cobrindo o caso vazio"
  - "0 ocorrências de '✓ Pipeline limpa' na saída do track quando não há nenhum commit ingerido — assert negativo no mesmo teste"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "Com zero commits ingeridos, o track informa que nada foi ingerido e orienta a rodar specharness connect repo, sem exibir '✓ Pipeline limpa'"
  - "Com pelo menos um commit ingerido e nenhum problema de higiene, o track mantém a saída atual, incluindo '✓ Pipeline limpa'"
---

## Contexto

A jornada ponta-a-ponta (2026-07-30) mostrou que `specharness track` executado
antes de qualquer ingestão (`specharness connect repo`) imprime
"Higiene: 0 vínculos válidos · 0 inválidos · 0 commits órfãos · 0 specs órfãs"
seguido de "✓ Pipeline limpa." — um falso positivo: a pipeline não está limpa,
está vazia. O usuário conclui que o vínculo commit→spec funciona quando na
verdade nenhum commit foi lido. Como na SPEC-017, é camada de apresentação:
o core já devolve as contagens necessárias.

## Fora de escopo

- Mudar o core (`linking.py`) ou o significado de `is_clean`.
- Disparar a ingestão automaticamente a partir do track.
- Alterar exit codes do track.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: track distingue pipeline vazia de pipeline limpa

  Cenário: pipeline vazia orienta a ingestão
    Dado um banco sem nenhum commit ingerido
    Quando o track roda
    Então a saída informa que nenhum commit foi ingerido e orienta a rodar specharness connect repo

  Cenário: pipeline vazia não é reportada como limpa
    Dado um banco sem nenhum commit ingerido
    Quando o track roda
    Então a saída não contém "✓ Pipeline limpa"

  Cenário: pipeline com commits e sem problemas continua limpa
    Dado commits ingeridos todos com trailer de spec válido
    Quando o track roda
    Então a saída contém "✓ Pipeline limpa"
```

## Notas de implementação

- Tudo em `packages/cli/src/specharness_cli/main.py` (`track` /
  `_render_track`); o core não muda.
- O caso vazio é detectado pela lista de commits lida do
  `RepositoryStore` antes de `link_commits` — zero commits ingeridos é
  propriedade da ingestão, não do resultado do linking.
- Step definitions do gate de BDD: `specs/steps/spec_029_steps.py`
  (`specharness verify SPEC-029 --steps specs/steps/spec_029_steps.py`).
