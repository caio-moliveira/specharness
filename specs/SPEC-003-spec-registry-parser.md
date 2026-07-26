---
spec: SPEC-003
title: "Spec Registry: parser, schema e ciclo de vida"
status: verifying
type: feature
owner: caio
created: 2026-07-25
updated: 2026-07-26
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-001]
adrs: [ADR-001]
success_metrics:
  - "100% dos arquivos specs/*.md deste repo parseiam sem erro"
  - "Property-based: 0 crashes não-tratados em 1.000 inputs aleatórios (Hypothesis, max_examples=1000 fixado no teste)"
  - "Cobertura de testes do módulo specschema >= 95%, sem `# pragma: no cover` em caminho exigido por critério de aceite"
  - "Todo caminho de erro do parser tem teste que asserta substring acionável da mensagem"
acceptance:
  - Spec válida (frontmatter + corpo) é parseada com todos os campos tipados
  - Documento sem frontmatter gera SpecParseError mencionando "frontmatter"
  - Frontmatter com YAML sintaticamente inválido gera SpecParseError mencionando "YAML"
  - Id fora do padrão SPEC-NNN gera SpecParseError mencionando "invalid spec id"
  - Transições de ciclo de vida fora da máquina de estados são rejeitadas
  - Rollback de um passo no ciclo de vida é aceito pela máquina de estados
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

  Cenário: frontmatter com YAML inválido é rejeitado com erro acionável
    Dado um arquivo markdown cujo frontmatter tem YAML sintaticamente inválido
    Quando o parser processa o arquivo
    Então uma SpecParseError é lançada mencionando "YAML"

  Cenário: id fora do padrão é rejeitado com erro acionável
    Dado um arquivo markdown com id "SPEC42" no frontmatter
    Quando o parser processa o arquivo
    Então uma SpecParseError é lançada mencionando "invalid spec id"

  Cenário: transição que pula o Readiness Gate é bloqueada
    Dado uma spec no status "approved"
    Quando o sistema tenta mover direto para "in_progress"
    Então a transição é rejeitada pela máquina de estados

  Cenário: rollback de um passo é aceito
    Dado uma spec no status "verifying"
    Quando o sistema tenta mover para "in_progress"
    Então a transição é aceita pela máquina de estados

  Cenário: blocos gherkin são extraídos do corpo
    Dado uma spec cujo corpo contém dois blocos cercados gherkin
    Quando o parser processa o arquivo
    Então exatamente dois blocos gherkin são disponibilizados para o gate
```

## Decisões e desvios

Registrados no readiness review de 2026-07-26. Os itens D2 e D3 são **desvios
do texto de SPEC-001 §7.2** — o código já os implementava sem registro.

**D1 — Campos obrigatórios são só `spec` e `title`.**
Todo o resto tem default (`status: draft`, `type: feature`, listas vazias).
Consequência deliberada: uma spec sem `acceptance` e sem `success_metrics`
*parseia*. Exigir não-vazio é trabalho do Readiness Gate (SPEC-010), não do
parser — o parser responde "isto é uma spec?", o gate responde "esta spec está
pronta?". Misturar os dois faria o hook de schema reprovar rascunho legítimo.

**D2 — O ciclo de vida aceita rollback de um passo.**
SPEC-001 §7.2 desenha uma cadeia linear
(`draft → approved → ready → in_progress → verifying → done → archived`) e
cala sobre volta atrás. A máquina implementada aceita um passo de retorno
(`approved → draft`, `ready → approved`, `in_progress → ready`,
`verifying → in_progress`), porque reprovação na verificação e spec devolvida
pelo gate são fluxos reais. Restrições que **permanecem**: `done → archived` é
o único caminho a partir de `done`, e `archived` é terminal (nenhuma saída).
Pular etapa à frente continua proibido — é o que o Readiness Gate protege.

**D3 — A máquina de estados não conhece os gates.**
`can_transition` valida apenas a *forma* do ciclo. Quem exige "passou no
Readiness Gate" (`approved → ready`) ou "BDD verde no CI" (`verifying → done`)
são os serviços que chamam a função, fora do domínio (ADR-001). Logo
`can_transition(READY, IN_PROGRESS) is True` sem tracker vinculado; a regra de
work item vive na camada de aplicação.

**D4 — Caveat de processo, não resolvido aqui.**
SPEC-003 está `in_progress` dependendo de SPEC-001, que segue em `draft`: o
contrato que esta spec implementa não está aprovado. Mudar o status do
documento fundador é decisão fora do escopo desta spec e fica registrada como
pendência.

**D5 — Métrica de property-based baixada de 10.000 para 1.000 inputs.**
A métrica original dizia 10.000, mas `test_parser_never_crashes_unexpectedly`
nunca teve `@settings`: rodava no default do Hypothesis (100 exemplos). O
número era afirmado, não medido — exatamente o que ADR-016 proíbe. Em vez de
inflar o teste até 10.000, a métrica passa a 1.000 **fixado via
`@settings(max_examples=1000)`**, para que o valor viva no código e não na
prosa. Custo medido: 0,69s no arquivo de teste inteiro (`uv run pytest` sobre
a property isolada) — barato o bastante para ficar na suíte padrão, sem
marker separado.
