# ADR-020 — Fronteira WorkItem-no-tracker / Spec-no-repo

- **Status:** aceita
- **Data:** 2026-07-28
- **Specs relacionadas:** SPEC-001, SPEC-007, SPEC-019

## Contexto

Ao planejar o adapter de Jira e a operação da comunidade, surgiu a pergunta:
o tracker (Jira/GitHub/Redmine) deveria ser a fonte de verdade também do
**conteúdo do Spec** — Definition of Ready, cenários BDD, métricas — e não só
do WorkItem? A tentação é centralizar tudo num board só. Mas o valor do
specharness depende de o Spec ser um artefato versionado no repositório: é ele
que o schema hook valida, que o review de PR discute linha a linha, que o
trailer `Spec:` amarra ao commit e que permite desenvolver o core sem banco e
sem API key. Precisamos fixar essa fronteira antes que ela se dissolva.

## Opções consideradas

1. **Jira como fonte de verdade do Spec** — um lugar só, board unificado.
   Contras: desliga o schema hook, o diff/review do Spec no PR, o trailer
   git↔Spec e o core-sem-infra; o produto vira "mais um Jira" e perde a tese
   verificável (readiness × turnover × percepção sobre dados versionados).
2. **Tracker dono do WorkItem, repo dono do Spec** — o tracker guarda backlog,
   status, sprint e US (ADR-007); o repo guarda o conteúdo do Spec em
   `specs/*.md`. Prós: preserva toda a esteira de qualidade e o dogfooding.
   Contra: dois lugares, com uma fronteira que precisa ser respeitada.

## Decisão

O tracker é a fonte de verdade do **WorkItem** (backlog, status, sprint, US);
o repositório continua dono do **Spec** (Ready, BDD, métricas) em `specs/*.md`.
São dois estágios do mesmo funil — WorkItem entra, passa no Readiness Gate,
*vira* Spec — não fontes concorrentes do mesmo dado. Nenhum campo tem duas
fontes de verdade: o write-back ao tracker se limita a status (ADR-007,
`StatusWriter`), nunca ao conteúdo do Spec.

Como consequência operacional: o board da **comunidade** roda no GitHub
Projects (atrito zero para o contribuidor, adapter de GitHub Issues já existe);
o **Jira** é construído como adapter dogfooded e prova de fit enterprise, não
como board obrigatório para contribuir.

## Consequências

- Fica mais fácil: manter a esteira de qualidade (hook, review, trailer) e a
  promessa de core-sem-infra; contribuir via GitHub sem conta de tracker.
- Fica mais difícil: manter a disciplina da fronteira — importar WorkItem do
  tracker é permitido, mas o conteúdo do Spec nunca é gerado a partir do
  tracker nem sincronizado de volta.
- Passa a ser proibido: adapter de tracker escrever conteúdo de Spec de volta
  no tracker; qualquer sync bidirecional que dê ao tracker autoria sobre Ready,
  BDD ou métricas.
