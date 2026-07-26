---
name: readiness-review
description: Avalia se uma spec está pronta para desenvolvimento (Definition of Ready — SPEC-001 §8.1), devolvendo score 0-100 e issues acionáveis. Use quando o usuário pedir para revisar uma spec, avaliar prontidão, rodar readiness, ou antes de mover uma spec para status ready.
---

# readiness-review

Este skill é o espelho manual do Readiness Gate do produto (SPEC-010/011).
Usamos no nosso próprio fluxo o que vendemos — divergências entre este
checklist e o gate implementado são bugs de um dos dois.

## Camada determinística (verifique mecanicamente)

- [ ] Frontmatter parseia (`just specs-validate`)
- [ ] `acceptance` tem ≥1 item; `success_metrics` tem ≥1 item mensurável
- [ ] Todo critério de aceite tem ≥1 cenário Gherkin que o cobre (monte a
      matriz critério × cenário e mostre)
- [ ] `depends_on` só referencia specs existentes e não-archived
- [ ] Cenários: `# language: pt`, um `Quando` por cenário, sem termos
      ambíguos ("rápido", "adequado", "amigável", "fácil", "intuitivo")

## Camada semântica (julgue como revisor sênior)

- Testabilidade real: cada `Então` é verificável por máquina ou por inspeção
  objetiva? Aponte os que não são.
- Ambiguidade: duas pessoas implementariam a mesma coisa lendo esta spec?
- Contradição: conflita com alguma spec `done`/`in_progress` ou ADR? Cite.
- Completude: os cenários cobrem o caminho triste (erros, vazios, timeouts)?

## Output obrigatório

```
Readiness: NN/100
Bloqueadores (impedem ready): ...
Recomendações (não bloqueiam): ...
Matriz critério × cenário: ...
```

Score <70 = não está ready. 70–89 = ready com ressalvas registradas.
≥90 = ready. Registre o resultado como comentário no PR ou na conversa.
