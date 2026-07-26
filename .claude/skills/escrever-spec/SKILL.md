---
name: escrever-spec
description: Cria ou edita uma spec do specharness no schema oficial (SPEC-001 §7) — frontmatter YAML validado, contexto, cenários BDD em Gherkin e métricas de sucesso mensuráveis. Use sempre que o usuário pedir para criar spec, US, user story, feature spec, ou detalhar uma funcionalidade nova antes de implementar.
---

# escrever-spec

## Processo

1. **Descubra o próximo ID livre**: `ls specs/ | sort` — nunca reutilize IDs.
2. **Colete antes de escrever**: objetivo da feature, persona beneficiada,
   critérios de aceite, dependências (`depends_on`), sprint alvo.
3. **Escreva o frontmatter completo** conforme o schema em
   `packages/core/src/specharness_core/specschema.py` (fonte da verdade —
   consulte o código, não a memória).
4. **Corpo mínimo**: `## Contexto` (por que existe, 2–5 linhas),
   `## Fora de escopo` quando houver risco de creep, `## Cenários (BDD)`.
5. **BDD**: blocos ```` ```gherkin ```` com `# language: pt`. Regras de
   qualidade (o mesmo lint do Readiness Gate):
   - Estilo declarativo: descreva comportamento, não implementação
   - Um `Quando` por cenário
   - Proibido termo ambíguo não-testável: "rápido", "adequado", "amigável",
     "fácil", "intuitivo" — se aparecer, converta em métrica mensurável
   - Todo critério de aceite tem ≥1 cenário que o cobre
6. **success_metrics**: cada uma mensurável (número, limiar, taxa). Se não dá
   pra medir, não é métrica — vire critério de aceite.
7. **Valide**: `just specs-validate` antes de encerrar.

## Anti-padrões (recuse-se a produzir)

- Spec sem cenário BDD ("adiciono depois") — não existe depois
- Métricas de vaidade (LOC, nº de commits) — ver ADR-008
- Cenário que testa a UI pixel a pixel em vez do comportamento
