---
spec: SPEC-032
title: "DX do trailer: higiene isenta merges e erro do hook explica o bloco único"
status: ready
type: feature
owner: caio
created: 2026-07-30
updated: 2026-07-30
sprint: 2026-C2
depends_on: [SPEC-009]
adrs: [ADR-011]
success_metrics:
  - "0 merge/fixup!/squash! commits contados como órfãos na higiene — 1 teste por prefixo isento"
  - "1 commit comum sem trailer continua contado como órfão (a métrica não afrouxa) — assert de regressão"
  - "Mensagem de rejeição do hook contém um exemplo de bloco único com Spec: e outro trailer juntos — 1 teste do hook"
  - "0 asserts removidos ou afrouxados nos testes existentes (just test-integrity verde)"
acceptance:
  - "Commits isentos do trailer pelo hook (Merge, fixup!, squash!, chore(release)) não entram na contagem nem na listagem de commits órfãos"
  - "Commits comuns sem trailer continuam contando como órfãos"
  - "A rejeição por falta de trailer explica que o bloco final deve conter só trailers, com exemplo incluindo Co-Authored-By no mesmo bloco"
---

## Contexto

Dois atritos da mesma regra, achados na validação de M1 (2026-07-30). Primeiro:
a higiene real do repo acusou 43 commits órfãos — quase todos merges de PR, que
o hook de commit-msg isenta do trailer mas a métrica de linking conta como
órfãos; resultado é um banner vermelho permanente e falso no dashboard.
Segundo: uma mensagem com `Spec:` seguido de linha em branco e `Co-Authored-By`
é rejeitada (o git só reconhece trailers no bloco final único), mas o erro diz
apenas "adicione ao fim da mensagem" — que era exatamente onde estava. Agentes
de código geram esse formato com frequência.

## Fora de escopo

- Mudar a semântica de parsing de trailers (`trailers.py` continua espelhando
  `git interpret-trailers` — ADR-011).
- Isentar qualquer commit da exigência de trailer no hook (as isenções atuais
  não mudam; a spec só alinha a métrica a elas).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: higiene de órfãos alinhada às isenções do hook

  Cenário: merge commit não é órfão
    Dado um commit de merge sem trailer de spec
    Quando o track processa os commits
    Então o commit de merge não entra na contagem de commits órfãos

  Cenário: fixup não é órfão
    Dado um commit fixup! sem trailer de spec
    Quando o track processa os commits
    Então o commit fixup não entra na contagem de commits órfãos

  Cenário: commit comum sem trailer segue órfão
    Dado um commit comum sem trailer de spec
    Quando o track processa os commits
    Então o commit entra na contagem de commits órfãos
```

```gherkin
# language: pt
Funcionalidade: rejeição do hook ensina o bloco único de trailers

  Cenário: erro mostra o bloco único com exemplo
    Dado uma mensagem de commit com Spec: separado dos demais trailers por linha em branco
    Quando o hook de commit-msg valida a mensagem
    Então a rejeição explica que todos os trailers devem ficar no mesmo bloco final e mostra um exemplo com Spec: e Co-Authored-By juntos
```

## Notas de implementação

- Core: predicado puro `is_trailer_exempt(message)` em `trailers.py` (mesmos
  prefixos do hook: `Merge `, `fixup!`, `squash!`, `chore(release)`);
  `linking.py` pula isentos ao contar/listar órfãos. O hook passa a importar o
  predicado — uma fonte para a regra, zero duplicação.
- Hook (`trailer_check.py`): a mensagem de "sem trailer" ganha o exemplo de
  bloco único (Spec: + Co-Authored-By no mesmo parágrafo) e a explicação de que
  linha em branco encerra o bloco de trailers.
