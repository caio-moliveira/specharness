---
spec: SPEC-028
title: "Dashboard embutido chama o próprio servidor (same-origin)"
status: approved
type: feature
owner: caio
created: 2026-07-29
updated: 2026-07-29
sprint: 2026-C2
tracker_refs: []
depends_on: [SPEC-021, SPEC-024]
adrs: [ADR-014, ADR-021]
success_metrics:
  - "Dashboard servido em host/porta diferentes do default resolve a API na mesma origem, sem apontar localhost:8321 (teste)"
  - "0 URLs absolutas de localhost embutidas no bundle de produção quando a variável de base não é definida (assert)"
acceptance:
  - Sem a variável de base definida, o bundle embutido resolve a API na mesma origem em que é servido
  - O modo de desenvolvimento continua a alcançar a API na porta separada, via variável de base explícita
---

## Contexto

O `up` serve dashboard e API na mesma porta (SPEC-021), mas o `api.ts` assa
`http://localhost:8321` como base quando `VITE_API_BASE_URL` não é definida — e o
build do bundle embutido não a define. Resultado: `up --port` ou `--host 0.0.0.0`
acessado de outra máquina faz o dashboard chamar `localhost:8321` e falhar. O
comentário do próprio `vite.config.ts` já diz "sem env, usa o mesmo host"; a
implementação é que discorda. O bundle embutido deve chamar a origem que o serve.

## Fora de escopo

- Remover a variável `VITE_API_BASE_URL`: ela permanece como override explícito,
  necessário ao modo de desenvolvimento (Vite em porta separada da API).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: dashboard embutido same-origin

  Cenário: bundle embutido resolve a API na origem que o serve
    Dado o dashboard embutido servido sem a variável de base definida
    Quando a página resolve a base da API
    Então a base é a mesma origem em que a página foi servida, não localhost:8321

  Cenário: desenvolvimento alcança a API na porta separada
    Dado o modo de desenvolvimento com a variável de base explícita
    Quando a página resolve a base da API
    Então a base aponta a porta separada da API definida na variável
```
