# brand/ — identidade visual do specharness

Direção **"Gate & Evidence"** (ADR-017): instrumento de engenharia, não
brinquedo de IA. Dark-first, denso, com proveniência em todo número.

## O monograma H-gate

O "h" de spec**h**arness desenhado como portão: duas hastes + travessa. A
travessa é o Readiness Gate. No dashboard, a altura da travessa pode codificar
o readiness score (baixa = draft, alta = ready) — o logo é um componente.

Arquivos: `logo.svg` (tile), `logo-mark*.svg` (glifo laranja/branco/preto),
`favicon.svg`, `wordmark-{dark,light}.svg`, `og-image.{svg,png}`,
`logo-512.png`.

## Paleta

| Token | Hex | Papel |
|---|---|---|
| Graphite | `#101014` | Fundo base (dark-first) |
| Panel | `#17171C` | Cards/superfícies |
| Border | `#26262E` | Bordas (no lugar de sombras) |
| Text | `#E7E7EA` / Muted `#8B8B96` | Texto |
| **Harness Orange** | `#F2542D` | Marca, ações, links, H-gate |
| **Evidence Green** | `#22C55E` | **SÓ** evidência provada |
| Amber | `#F59E0B` | Readiness 70–89 / pendente |
| Red | `#EF4444` | Readiness <70 / falha |

### As duas regras que não se negociam

1. **Verde nunca é decoração.** Verde aparece exclusivamente quando algo foi
   *provado* (BDD verde no CI, eval passou, gate aprovou). Um botão verde
   "salvar" é bug de design.
2. **Todo número tem proveniência.** Métricas exibidas carregam o chip de
   origem ("via CI run #142"). Número sem proveniência não entra em tela —
   é o ADR-016 como linguagem visual.

## Tipografia

- **Inter** — UI (400/500/600), display em 600 com tracking -0.02em
- **JetBrains Mono** — código, IDs de spec (`SPEC-009`), trailers e TODOS os
  números de métricas (`tabular-nums`)

## Status de spec → cor

draft `muted` · approved `text outline` · ready `readiness-high outline` ·
in_progress `orange` · verifying `amber` · done `evidence green` (o único
status que "ganha" o verde — porque done é provado pelo CI) · archived
`muted` riscado.

## Uso

- `tokens.css` → importar no web/ (shadcn-compatible) — SPEC-016
- Não recolorir o glifo fora das três variantes; não aplicar gradientes
- Preview vivo: `preview.html`
