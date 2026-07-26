---
spec: SPEC-003
title: "Spec Registry: parser, schema e ciclo de vida"
status: in_progress
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-001]
adrs: [ADR-001]
success_metrics:
  - "100% dos arquivos specs/*.md deste repo parseiam sem erro"
  - "Property-based: 0 crashes não-tratados em 10.000 inputs aleatórios (Hypothesis)"
  - "Cobertura de testes do módulo specschema >= 95%"
acceptance:
  - Spec válida (frontmatter + corpo) é parseada com todos os campos tipados
  - Documento sem frontmatter, YAML inválido ou id fora do padrão gera SpecParseError com mensagem acionável
  - Transições de ciclo de vida fora da máquina de estados são rejeitadas
  - Blocos gherkin do corpo são extraíveis para o Readiness Gate
---

## Contexto

Tudo no specharness deriva da spec como contrato (SPEC-001 §7). O parser é a
primeira peça de código e a mais crítica: hooks, gate, track, verify e report
dependem dele. Input é adversarial por natureza (arquivos editados à mão).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: parsing de specs do registry

  Cenário: spec válida é parseada por completo
    Dado um arquivo markdown com frontmatter YAML válido e id "SPEC-042"
    Quando o parser processa o arquivo
    Então o resultado expõe id, status, métricas de sucesso e corpo tipados

  Cenário: documento sem frontmatter é rejeitado com erro acionável
    Dado um arquivo markdown sem bloco de frontmatter
    Quando o parser processa o arquivo
    Então uma SpecParseError é lançada mencionando "frontmatter"

  Cenário: transição que pula o Readiness Gate é bloqueada
    Dado uma spec no status "approved"
    Quando o sistema tenta mover direto para "in_progress"
    Então a transição é rejeitada pela máquina de estados

  Cenário: blocos gherkin são extraídos do corpo
    Dado uma spec cujo corpo contém dois blocos cercados gherkin
    Quando o parser processa o arquivo
    Então exatamente dois blocos gherkin são disponibilizados para o gate
```
