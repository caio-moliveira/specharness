---
spec: SPEC-025
title: "Dashboard sem rótulos internos do specharness"
status: ready
type: feature
owner: caio
created: 2026-07-29
updated: 2026-07-29
sprint: 2026-C2
tracker_refs: []
depends_on: [SPEC-016, SPEC-024]
adrs: [ADR-017, ADR-021]
success_metrics:
  - "0 ocorrências de 'Fase A', 'SPEC-0' ou 'just ' nas respostas /api/* e nos textos da UI servida (assert)"
  - "phase deixa de ser constante: com sprint informado o campo reflete o valor real ou null, nunca 'Fase A' fixo (teste)"
acceptance:
  - O campo phase servido em /api/big-picture não expõe a fase interna do roadmap do specharness
  - Os chips de proveniência exibem rótulos genéricos, sem IDs de spec internas como SPEC-013 ou SPEC-014
  - O texto do estágio review no pipeline não cita nenhuma spec interna do specharness
  - As mensagens da UI referenciam comandos do produto (specharness), não recipes internas do repositório (just)
---

## Contexto

O dashboard live (SPEC-024) serve, no produto instalado, valores que só fazem
sentido dentro do repositório do próprio specharness: a constante `phase="Fase A"`
(fase do roadmap interno, SPEC-001 §5), chips de proveniência com os IDs `SPEC-013`
e `SPEC-014`, o texto do estágio *review* citando `SPEC-013`, e mensagens que
mandam rodar `just serve`/`just dev` (recipes internas, não comandos do usuário).
Nada disso é dado do projeto do usuário — é vazamento de rótulo interno no produto.

## Fora de escopo

- Mudar o CONTRATO da API: os campos (`phase`, `data_source`, etc.) permanecem;
  só a FONTE/rótulo muda. A web continua lendo `data.phase`.
- Ingerir eventos de review (o estágio segue `unavailable`); aqui só se corrige o
  texto, não o comportamento do estágio.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: dashboard sem rótulos internos do specharness

  Cenário: phase não expõe a fase interna do roadmap
    Dado um repositório do usuário com um sprint próprio no registry
    Quando o Tech Lead carrega a big picture live
    Então o campo phase reflete o contexto do usuário ou fica null, nunca a constante "Fase A"

  Cenário: chips de proveniência com rótulos genéricos
    Dado a big picture carregada com dados reais
    Quando o Tech Lead inspeciona os chips de proveniência dos números
    Então cada chip mostra a origem genérica (snapshot, survey) sem citar SPEC-013 ou SPEC-014

  Cenário: estágio review sem citar spec interna
    Dado o pipeline de uma spec qualquer do usuário
    Quando o estágio review é exibido como indisponível
    Então o texto do estágio review não cita nenhuma spec interna do specharness

  Cenário: mensagens da UI apontam comandos do produto
    Dado o dashboard servido pelo produto instalado
    Quando a UI mostra o banner de demo ou o erro de carregamento
    Então as mensagens instruem comandos do specharness, não recipes internas com just
```
