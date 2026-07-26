# ADR-004 — Harness profiles como dados versionados, não código

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

As boas práticas oficiais de Anthropic, OpenAI e Moonshot mudam a cada poucos meses. Hardcodá-las no core faria o produto nascer desatualizado.

## Opções consideradas

1. Práticas embutidas em templates no código — exige release para cada mudança de vendor
2. Profiles como pacotes de dados (YAML+markdown) com fonte citada — comunidade atualiza via PR simples

## Decisão

profiles/<runtime>/ contém práticas, templates e checks como dados versionados. Toda recomendação cita a fonte oficial (URL + data); profile.yaml carrega reviewed_at e o wizard avisa quando envelhece.

## Consequências

Atualização de profile é a good first issue canônica do projeto; exige disciplina de citação.
