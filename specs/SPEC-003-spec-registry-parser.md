---
spec: SPEC-003
title: "Spec Registry: parser, schema e ciclo de vida"
status: done
type: feature
owner: caio
created: 2026-07-25
updated: 2026-07-26
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-001]
adrs: [ADR-001]
success_metrics:
  - "100% dos arquivos specs/SPEC-*.md deste repo parseiam sem erro"
  - "Property-based: 0 crashes não-tratados em 1.000 inputs aleatórios (Hypothesis, max_examples=1000 fixado no teste)"
  - "Cobertura de testes do módulo specschema >= 95%, sem `# pragma: no cover` em caminho exigido por critério de aceite"
  - "Todo caminho de erro do parser tem teste que asserta substring acionável da mensagem"
  - "Mutation score do módulo specschema >= 90% (`just mutants`), com sobreviventes registrados no corpo da spec"
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

**D5 — Métrica de property-based fixada em 1.000 inputs (era 10.000).**
Duas coisas separadas aqui.

*O defeito:* a métrica dizia 10.000, mas
`test_parser_never_crashes_unexpectedly` nunca teve `@settings` — rodava no
default do Hypothesis, 100 exemplos. O número era afirmado e nunca medido,
exatamente o que ADR-016 proíbe. Corrigido fixando
`@settings(max_examples=1000)`: o valor passa a viver no código, e quem roda a
suíte mede o que a spec promete.

*A escolha do número:* 1.000 é **decisão de escopo do dono do projeto**, não
consequência de custo. O custo foi medido depois e não justifica a redução —
1.000 exemplos gastam 0,27s de generate phase
(`--hypothesis-show-statistics`), então 10.000 custariam ~2,7s, o que caberia
na suíte padrão sem incômodo. Registrado assim para a decisão ficar
auditável: voltar a 10.000 é trocar um literal, e o argumento contra não é
técnico.

**D6 — Mutation score é o critério de parada da verificação.**
Três rodadas de verificação adversarial reprovaram esta spec sem achar **um
único bug de produção**: todos os bloqueadores foram lacunas de teste, e o
verificador registrou "produção está correta" nos casos que checou. A causa
não era a implementação, era a redação: critérios como "todos os campos
tipados" e "todo caminho de erro tem teste" são quantificadores universais, e
teste de mutação sempre encontra um contraexemplo novo. Critério
infalsificável em tempo finito não é critério — é esteira.

Substituído por um número medível: `just mutants` aplica um catálogo
declarado de mutantes em `specschema.py` e falha abaixo de 90%. Cobertura de
linha diz que o teste *executou* o código; o mutation score diz que ele
*provaria* uma quebra — foi exatamente a diferença que as três rodadas
expuseram (100% de cobertura com mutantes vivos).

Mutantes equivalentes ficam fora do catálogo de propósito, com justificativa
no script: incluí-los rebaixa o score sem apontar defeito. Exemplo real desta
spec: trocar `.match` por `.search` no frontmatter não altera comportamento,
porque o padrão já começa com `\A`.

Medido: **32/32 = 100%** (`just mutants`, limiar 90%).

**D7 — Follow-ups aceitos, não fechados nesta entrega.**
Registrados porque a 3ª verificação os apontou e a decisão foi seguir:

1. *Campos tipados sem assert individual.* `owner`, `updated`, `sprint`,
   `version` e `tracker_refs` estão na fixture `VALID_SPEC` e são parseados,
   mas não têm assert dedicado — um mutante que os descartasse via `alias`
   sobreviveria. O critério "todos os campos tipados" está coberto para os 9
   campos restantes.
2. *O property test exercita um ramo só.* Os 1.000 textos aleatórios morrem
   todos no regex de abertura; rodando isolado, cobre 73% do módulo, sem
   tocar `yaml.safe_load` nem `model_validate`. Gerar documentos **em forma
   de** frontmatter cobriria o resto — mudar o número de exemplos, não.
3. *Métrica 1 não é gate local.* `just lint && just test` não roda
   `specs-validate`; uma regressão que quebrasse uma spec real só apareceria
   no CI. Sugere um `just check` agregado.
4. *Gate de cobertura do CI é 85% no pacote*, contra os 95% do módulo que
   esta spec promete. Exige mudar `.github/workflows/`, que pede confirmação
   humana.
5. *`just mutants` não roda no CI.* A métrica de mutação é local; apodrece
   pelo mesmo motivo do item 4 e exige a mesma confirmação humana.
6. *Sobreviventes fora do catálogo, aceitos por baixa severidade.* Uma sonda
   independente na 4ª verificação achou seis, nenhum ligado a critério de
   aceite: os valores de string de `SpecStatus.IN_PROGRESS`, `ARCHIVED` e
   `SpecType.HARNESS` (nada amarra membro do enum ao wire format), `\d{3,}`
   → `\d{3}` no id (rejeitaria SPEC-1000 em diante), `except yaml.YAMLError`
   → `except Exception`, e o `.lstrip()` do corpo. Registrados aqui para
   serem escopo declarado, não redescoberta na próxima rodada.

**Nota sobre a aritmética do score.** 100% é relativo ao catálogo declarado
em `scripts/mutants.py`, não ao universo de mutações possíveis do módulo. Com
os cinco campos do item 1 incluídos seriam 32/37 = 86,5%; somado o conjunto
independente da 4ª verificação, 32/44 = 72,7%. A métrica se define como
"(`just mutants`)" de propósito — um catálogo versionado e auditável vale
mais que um número absoluto inatingível —, mas o leitor deve saber que o
denominador é uma escolha registrada, não uma lei da natureza.
