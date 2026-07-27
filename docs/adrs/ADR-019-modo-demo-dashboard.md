# ADR-019 — Modo demo do dashboard: banco dedicado, rótulo DEMO e origem declarada

- **Status:** aceita
- **Data:** 2026-07-27
- **Specs relacionadas:** SPEC-018, SPEC-016

## Contexto

O seed do dashboard (SPEC-016) existe para um contribuidor de frontend rodar
`just dev` sem conexões externas. Mas ele grava no banco resolvido pelo
ambiente: num checkout novo, os dados fictícios (snapshot, percepção, commits
sob o slug real) entram no banco real do usuário, na sprint corrente do
projeto (`2026-A4`), e ficam indistinguíveis dos dados reais para sempre — a
guarda de idempotência é "existe série da sprint", não "é seed", e o desenho
append-only (SPEC-013) impede apagar séries com segurança. A avaliação de
adoção de 2026-07-27 confirmou o dano à confiança: números de demo lidos como
reais, sem qualquer sinalização na UI.

## Opções consideradas

1. **Só renomear a sprint do seed (ex.: `DEMO-2026-A1`)** — pró: mudança de uma
   linha. Contra: não descontamina — os commits falsos entram sob o slug real e
   poluem `track`, `report` e higiene qualquer que seja a sprint; e como
   `current_sprint` escolhe pelo registry em disco, um snapshot `DEMO-*` nunca
   seria selecionado num repo real (o demo sumiria da big picture).
2. **Marcador de seed em `schema_meta`** — pró: proveniência dentro do próprio
   banco. Contra: exige migração nova e só *detecta* a mistura; não a impede.
3. **Banco demo dedicado + flag de ambiente + rótulo DEMO + origem no
   contrato** — pró: o seed fica *incapaz* de tocar o banco real por
   construção; a origem é declarada fim a fim (API → UI); `just dev` segue
   zero-config. Contra: um arquivo SQLite a mais e um campo novo no contrato
   OpenAPI (regeneração do client — ADR-014).

## Decisão

Opção 3: o seed escreve exclusivamente em `.specharness/demo.db`
(`demo_target()`), com `SEED_SPRINT = "DEMO-2026-A1"`; o server em
`SPECHARNESS_DEMO=1` (setada pelo `just dev`) serve o banco demo, responde
`data_source: "demo"` e defaulta a sprint da big picture para a sprint demo; a
UI exibe aviso visível quando a origem é demo. Isolamento por construção vale
mais que detecção: uma ferramenta cuja tese é "métricas em que se pode
confiar" não pode semear dados fictícios no banco que mede.

## Consequências

- Mais fácil: onboarding de frontend continua `just dev` zero-config; apagar o
  demo é deletar um arquivo; nenhum dado demo aparece em `track`/`report`
  reais.
- Mais difícil: mudanças no contrato exigem regenerar `web/openapi.json`
  (comando no `web/README.md`); o server passa a ter dois alvos de banco
  possíveis, escolhidos por env.
- Passa a ser proibido: seed escrevendo em banco resolvido do ambiente, e
  qualquer resposta da API de dashboard sem `data_source` declarado.
- Remediação de bancos já contaminados (seed antigo em sprint real): manual —
  inspecionar `metric_snapshots`/`perception_samples`/`commits` pela assinatura
  do seed (timestamp fixo `2026-07-27T00:00:00Z`, commits `a1`/`b2`/`c3`) e
  removê-los, ou recriar o banco reingerindo o histórico. Não automatizar
  (append-only).
