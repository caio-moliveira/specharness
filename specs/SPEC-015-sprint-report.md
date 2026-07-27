---
spec: SPEC-015
title: "report: relatório de sprint (tabular determinístico + narrativa LLM)"
status: in_progress
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-013, SPEC-014]
adrs: [ADR-006]
success_metrics:
  - "Geração do relatório tabular de uma sprint com 20 specs em < 10s"
  - "Narrativa LLM: 0 números divergentes dos dados tabulares (verificado por checagem automática pós-geração)"
  - "100% dos casos do golden dataset de narrativa verdes nos modelos suportados"
acceptance:
  - Relatório tabular inclui specs concluídas vs planejadas, first-run pass rate, cycle time, turnover, órfãos e agregados de percepção
  - Narrativa LLM é opcional e derivada exclusivamente dos dados tabulares; toda afirmação numérica é conferida contra a tabela
  - Saída em markdown por padrão; exportação docx disponível
  - Sem LLM disponível, o relatório tabular completo é gerado normalmente
---

## Contexto

A entrega da Fase 6 que hoje alguém escreve na mão. Determinístico no
conteúdo, LLM apenas na prosa — com checagem automática de que a narrativa
não inventa números (citação fiel aos dados é o read-before-cite do produto).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: relatório de sprint

  Cenário: relatório tabular sem LLM
    Dado uma sprint encerrada com métricas calculadas e nenhum LLM disponível
    Quando o report é gerado
    Então o relatório tabular completo é produzido em markdown

  Cenário: narrativa fiel aos dados
    Dado uma sprint com métricas calculadas e LLM configurado
    Quando o report com narrativa é gerado
    Então cada número citado na narrativa confere com a tabela correspondente

  Cenário: narrativa com número divergente é rejeitada
    Dado uma narrativa gerada contendo um valor que não existe nos dados
    Quando a checagem pós-geração executa
    Então a narrativa é rejeitada e regenerada com o erro apontado

  Cenário: exportação em docx
    Dado um relatório gerado em markdown
    Quando o usuário solicita exportação docx
    Então o arquivo docx é produzido com o mesmo conteúdo
```

## Notas de implementação

Escopo fechado no readiness (2026-07-27). Decisões:

- **Conteúdo determinístico, LLM só na prosa (ADR-006).** O relatório tabular é
  montado no core puro dos dados já materializados: métricas da SPEC-013 (snapshot),
  percepção da SPEC-014 (agregado) e vínculos/órfãos da SPEC-009 (`LinkingResult`).
  Sem LLM, o tabular completo sai normalmente.
- **Read-before-cite (acceptance[2], cenário do número divergente).** `narrative_
  divergences` extrai todo número citado na narrativa e recusa qualquer um que não
  apareça literalmente na tabela. É core puro; a geração (adapter) regenera com os
  números ofensores apontados, até um limite de tentativas. `complete` é injetável
  (o `LiteLlmClient.complete` da SPEC-005), então a narrativa roda hermética em teste.
- **docx por gerador interno (stdlib).** Sem nova dependência: um .docx é um zip de
  poucas partes WordprocessingML, escritas à mão com `zipfile` — mesma postura de
  "gerador interno" dos parsers de trailers/gherkin. Cada linha do markdown vira um
  parágrafo, então o docx carrega o mesmo conteúdo.
- **Golden de narrativa (success_metric 3).** Um conjunto curado (tabela + narrativa
  + veredito esperado) valida o checker de forma determinística; a parte "em todos os
  modelos suportados" é medida em runtime no CI (como os evals da SPEC-011).
