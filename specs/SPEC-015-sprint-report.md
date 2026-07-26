---
spec: SPEC-015
title: "report: relatório de sprint (tabular determinístico + narrativa LLM)"
status: approved
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
  - "Golden dataset de narrativa verde em todos os modelos suportados"
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
