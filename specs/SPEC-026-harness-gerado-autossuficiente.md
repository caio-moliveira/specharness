---
spec: SPEC-026
title: "Harness gerado auto-suficiente no repo do usuário"
status: verifying
type: harness
owner: caio
created: 2026-07-29
updated: 2026-07-29
sprint: 2026-C2
tracker_refs: []
depends_on: [SPEC-022, SPEC-023]
adrs: [ADR-003, ADR-004, ADR-021]
success_metrics:
  - "0 referências a ferramenta ou caminho não provisionado pelo init nos arquivos gerados (assert sobre o texto renderizado)"
  - "Com tracker none, 0 ocorrências do literal 'none' nos 3 renderers do harness (AGENTS.md, camada do agente, specs/README) (teste)"
acceptance:
  - O AGENTS.md gerado não instrui o agente a rodar uma ferramenta que o init não provisiona no repositório do usuário
  - A camada do agente não referencia caminhos internos do specharness, como profiles, que o init não cria no repositório do usuário
  - Com tracker none, os três arquivos gerados descrevem o backlog local em specs, sem exibir o literal none ao usuário
---

## Contexto

O `init` gera o harness (SPEC-023) com instruções que apontam ferramentas e
caminhos que ele NÃO provisiona no repo do usuário: o `AGENTS.md` manda "passar
pelo `verificar-spec`" (um subagente que só existe no repositório do specharness)
e a camada do agente diz derivar de `profiles/{agent}` (diretório não copiado).
Além disso, com `tracker=none`, o `render_agents_md` mostra "o backlog local em
specs/", mas a camada e o `specs/README` exibem o literal cru `(none)`. O harness
gerado tem de ser auto-suficiente: referenciar só o que existe no repo do usuário.

## Fora de escopo

- Alterar a espinha fixa do método (Readiness Gate, trailer, BDD, anti-vigilância)
  — a verificação adversarial permanece como princípio; muda-se apenas como o
  texto gerado a expressa, para não implicar uma ferramenta ausente.
- Copiar o diretório `profiles/` do specharness para o repo do usuário.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: harness gerado auto-suficiente

  Cenário: AGENTS.md não manda rodar ferramenta ausente
    Dado um repositório recém-inicializado pelo init
    Quando o agente lê o AGENTS.md gerado
    Então nenhuma instrução manda rodar uma ferramenta que o init não provisiona no repositório

  Cenário: camada do agente sem caminho interno inexistente
    Dado a camada do agente gerada pelo init
    Quando o agente procura os caminhos citados
    Então a camada não referencia profiles nem outro caminho interno que o init não cria

  Cenário: tracker none descrito sem literal cru
    Dado um init com tracker none
    Quando os três arquivos do harness são gerados
    Então cada um descreve o backlog local em specs sem exibir o literal none ao usuário
```
