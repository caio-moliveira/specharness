---
expected_range: [85, 100]
notes: "Spec completa: critérios cobertos por cenários, métricas mensuráveis, sem termos ambíguos."
---
```markdown
---
spec: SPEC-901
title: "Exportação de relatório de pipeline em CSV"
status: draft
type: feature
success_metrics:
  - "Exporta 10.000 linhas em < 5s"
  - "100% das colunas do schema presentes no arquivo"
acceptance:
  - Cada linha do pipeline vira uma linha do CSV com colunas fixas
  - Exportação de pipeline vazio gera arquivo apenas com o cabeçalho
  - Caractere especial na descrição é escapado conforme RFC 4180
---

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: exportação de pipeline em CSV

  Cenário: pipeline com linhas vira CSV
    Dado um pipeline com três itens
    Quando a exportação em CSV é executada
    Então o arquivo tem três linhas de dados e um cabeçalho com as colunas fixas

  Cenário: pipeline vazio gera só o cabeçalho
    Dado um pipeline sem nenhum item
    Quando a exportação em CSV é executada
    Então o arquivo tem apenas a linha de cabeçalho

  Cenário: descrição com caractere especial é escapada
    Dado um item cuja descrição contém vírgula e aspas
    Quando a exportação em CSV é executada
    Então o campo é escapado conforme a RFC 4180
```
```
