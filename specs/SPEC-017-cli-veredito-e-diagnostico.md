---
spec: SPEC-017
title: "CLI: veredito consolidado do ready e diagnóstico acionável (perception, track)"
status: in_progress
type: feature
owner: caio
created: 2026-07-27
updated: 2026-07-27
sprint: 2026-A5
depends_on: [SPEC-009, SPEC-010, SPEC-011, SPEC-014]
adrs: [ADR-016]
success_metrics:
  - "100% dos caminhos de saída do ready terminam com linha 'Veredito:' (6 caminhos: piso reprova, piso ok sem LLM, erro LLM, score < limiar, aprovada, override) — 1 teste de CLI por caminho"
  - "perception distingue as 4 causas de gap indisponível (sem amostras, sem snapshot, sem cycle time, sem amostra comparável) — 1 teste por causa"
  - "track --orphans lista 100% dos SHAs órfãos até o limite pedido, com rodapé indicando quantos ficaram de fora"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "Todo término do ready — sucesso, bloqueio ou override — imprime uma linha final 'Veredito: PRONTA' ou 'Veredito: BLOQUEADA — <motivo>', sem remover nenhuma mensagem atual"
  - "ready --json emite o veredito legível por máquina no padrão do verify (verdict, motivo, piso e camada LLM), com os mesmos exit codes"
  - "Quando o gap de percepção é indisponível, a dica aponta a causa real e a ação que resolve — nunca uma ação que não muda o resultado"
  - "track --orphans lista os SHAs truncados dos commits órfãos, com --limit para controlar o tamanho da saída"
---

## Contexto

A avaliação de adoção (jornada caixa-preta, 2026-07-27) mostrou três atritos no
uso real da CLI: o `ready` imprime vereditos parciais e sai com código 1 sem uma
linha final que responda "está pronta ou não?" (pior caso: "o piso passou" seguido
de exit 1); o `perception` sugere rodar `specharness metrics` quando o gap é
indisponível, mas essa é só 1 das 4 causas possíveis — nas outras 3 a dica manda
o usuário para o lugar errado; e o `track` conta commits órfãos sem listá-los,
deixando a parte acionável do relatório de higiene inacessível. Tudo aqui é
camada de apresentação: o core já produz os dados necessários.

## Fora de escopo

- Mudar a semântica dos exit codes do `ready` (1 continua significando bloqueio,
  inclusive sem provedor LLM — ADR-006).
- Alterar o cálculo do gap de percepção no core (`perception.py`) ou o desenho
  append-only das séries de métricas.
- Paginação ou filtros novos no `track` além de `--orphans`/`--limit`.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: veredito consolidado do ready

  Cenário: piso determinístico reprovado termina com veredito
    Dado uma spec que reprova no piso determinístico do Readiness Gate
    Quando o ready roda sobre ela
    Então a saída termina com "Veredito: BLOQUEADA" e o número de bloqueadores

  Cenário: piso aprovado sem provedor LLM é bloqueio explícito
    Dado um ambiente sem nenhum provedor LLM configurado
    Quando o ready roda sobre uma spec que passa no piso determinístico
    Então o aviso de camada semântica pendente permanece e a saída termina com "Veredito: BLOQUEADA" citando a camada semântica

  Cenário: spec aprovada nas duas camadas termina com veredito PRONTA
    Dado uma spec que passa no piso determinístico e na camada LLM
    Quando o ready roda sobre ela
    Então a saída termina com "Veredito: PRONTA"

  Cenário: score abaixo do limiar termina com veredito e motivo
    Dado uma spec cuja avaliação LLM fica abaixo do limiar
    Quando o ready roda sobre ela
    Então a saída termina com "Veredito: BLOQUEADA" citando o score e o limiar

  Cenário: override auditado termina com veredito
    Dado um override registrado com autor e justificativa
    Quando o ready roda com a opção de override
    Então a saída termina com "Veredito: PRONTA" citando o override

  Cenário: veredito legível por máquina
    Dado uma spec avaliada pelo Readiness Gate
    Quando o ready roda com --json
    Então a saída é um JSON com verdict, motivo, resultado do piso e da camada LLM
```

```gherkin
# language: pt
Funcionalidade: diagnóstico do gap de percepção

  Cenário: sem amostras a dica manda coletar percepção
    Dado uma sprint sem nenhuma amostra de percepção
    Quando o perception roda
    Então a dica de gap indisponível manda coletar com specharness survey

  Cenário: sem snapshot a dica manda computar métricas
    Dado uma sprint com amostras de percepção e nenhum snapshot de métricas
    Quando o perception roda
    Então a dica de gap indisponível manda rodar specharness metrics

  Cenário: snapshot sem cycle time explica a causa real
    Dado um snapshot cujas specs não têm cycle time
    Quando o perception roda
    Então a dica explica que faltam transições ready até done no histórico e que recalcular métricas não muda o resultado

  Cenário: amostras sem spec comparável são apontadas
    Dado amostras de percepção cujas specs não aparecem com cycle time no snapshot
    Quando o perception roda
    Então a dica explica que nenhuma amostra é de spec com cycle time conhecido
```

```gherkin
# language: pt
Funcionalidade: listagem de commits órfãos no track

  Cenário: órfãos são listáveis sob demanda
    Dado commits ingeridos sem trailer de spec
    Quando o track roda com --orphans
    Então os SHAs truncados dos commits órfãos aparecem na saída

  Cenário: sem a opção a saída permanece um resumo
    Dado commits ingeridos sem trailer de spec
    Quando o track roda sem opções
    Então os órfãos aparecem apenas como contagem no relatório de higiene

  Cenário: a listagem respeita o limite
    Dado mais commits órfãos do que o limite pedido
    Quando o track roda com --orphans e um limite
    Então a saída lista até o limite e informa quantos ficaram de fora
```

## Notas de implementação

- Tudo em `packages/cli/src/specharness_cli/main.py`; o core não muda.
- `ready`: helper único de veredito chamado antes de cada `typer.Exit` nos seis
  caminhos de término (piso reprova; piso ok sem provedor; erro LLM; score
  abaixo do limiar; aprovada; `--override`). As mensagens atuais permanecem —
  o veredito é uma linha adicional de fechamento. `--json` segue o padrão do
  `verify` (`_emit_verify_json`): JSON no stdout, tabelas suprimidas, exit
  codes inalterados.
- `perception`: o comando já tem `snapshot`, `cycle_times` e o agregado em
  mãos; o diagnóstico diferencia as causas com precedência fixa (sem amostras →
  sem snapshot → sem cycle time → sem amostra comparável) para ser
  determinístico nos testes.
- `track`: `LinkingResult.orphan_commits` já traz os SHAs completos do core;
  a flag só os apresenta (truncados como no restante do render), com `--limit`
  (default 20) e rodapé quando truncar.
