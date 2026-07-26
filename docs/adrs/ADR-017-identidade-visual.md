# ADR-017 — Identidade visual "Gate & Evidence"

- **Status:** aceita
- **Data:** 2026-07-26
- **Specs relacionadas:** SPEC-001, SPEC-016

## Contexto

O produto precisa de identidade antes do scaffold web (SPEC-016) e do
lançamento público. O território dos dev tools de IA está saturado de
roxo/azul sobre dark genérico; ao mesmo tempo, a tese do specharness
(evidência acima de auto-relato, ADR-016) pode e deve ser expressa
visualmente.

## Opções consideradas

1. **Verde-terminal como acento principal** — leitura imediata de "dev tool",
   mas território ocupado (Supabase, Cucumber) e queimaria o verde como cor
   semântica de evidência.
2. **Azul-blueprint** — competente e seguro, invisível na multidão.
3. **"Gate & Evidence"** — grafite dark-first + Harness Orange (#F2542D,
   do equipamento de segurança físico — literalmente harness), verde
   reservado exclusivamente a evidência provada, monograma H-gate.

## Decisão

Direção "Gate & Evidence": monograma **H-gate** (o "h" como portão; a
travessa é o Readiness Gate e pode codificar o score no dashboard);
paleta grafite `#101014` + **Harness Orange `#F2542D`**; tipografia Inter
(UI) + JetBrains Mono (contratos: IDs, trailers, números com tabular
figures); densidade Linear, bordas em vez de sombras, radius 6px. Duas
regras inegociáveis: **verde nunca é decoração** (aparece só quando algo
foi provado por CI/gate/eval) e **todo número exibido carrega chip de
proveniência** — o ADR-016 como linguagem visual. Artefatos e tokens em
`brand/`; `tokens.css` é a fonte para o tema shadcn do web/.

## Consequências

Identidade diferenciada no território e coerente com a tese; o logo vira
componente funcional do dashboard. Custo: disciplina de revisão de UI para
as duas regras (um botão verde "salvar" é bug de design, não preferência).
