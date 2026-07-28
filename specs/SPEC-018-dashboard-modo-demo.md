---
spec: SPEC-018
title: "Dashboard: modo demo honesto — seed isolado, origem declarada e pipeline localizado"
status: verifying
type: feature
owner: caio
created: 2026-07-27
updated: 2026-07-27
sprint: 2026-A5
depends_on: [SPEC-016]
adrs: [ADR-014, ADR-017, ADR-019]
success_metrics:
  - "0 escritas do seed fora de .specharness/demo.db (provado por teste que roda o seed com SPECHARNESS_DATABASE_URL apontando para outro banco)"
  - "100% das respostas da API em modo demo carregam data_source=demo; 100% fora dele carregam data_source=live (1 teste por modo)"
  - "0 strings pt-BR hardcoded renderizadas na UI em inglês: os 5 estágios do pipeline usam chave de tradução + contagem (provado por teste do contrato)"
  - "cov-server ≥ 90% mantida (just cov-server)"
acceptance:
  - "Rodar o seed nunca escreve no banco resolvido do ambiente — os dados demo vivem num banco dedicado (.specharness/demo.db) com sprint rotulada DEMO-"
  - "A resposta da big picture declara a origem dos dados (live ou demo) e a interface exibe um aviso visível quando a origem é demo"
  - "just dev continua zero-config (sobe com seed no banco demo); uma receita serve o banco real do projeto sem seed e sem aviso"
  - "Os detalhes dos estágios do pipeline chegam como chave estruturada + contagem e são renderizados no idioma selecionado na interface"
---

## Contexto

A avaliação de adoção (2026-07-27) expôs dois riscos do seed do dashboard
(SPEC-016): o `just dev` roda o seed no banco resolvido pelo ambiente — num
checkout novo isso grava métricas, percepção e commits fictícios no banco real
do usuário, na mesma sprint do projeto (`2026-A4`), indistinguíveis para sempre
dos dados reais (a guarda de idempotência é "existe série da sprint", não "é
seed"). Além disso, a UI mistura registry real com números do banco sem
declarar a origem, e os `detail` do pipeline chegam em pt-BR hardcoded mesmo
com a interface em inglês. A decisão de isolamento está registrada na ADR-019.

## Fora de escopo

- Remediação automática de bancos já contaminados por seed antigo (o desenho
  append-only impede apagar séries com segurança; a limpeza manual está
  documentada na ADR-019).
- Localizar a narrativa do report ou mensagens da CLI (só o dashboard).
- Autenticação ou escrita no dashboard (segue read-only, SPEC-016).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: modo demo do dashboard

  Cenário: seed nunca escreve no banco do projeto
    Dado um ambiente cujo banco resolvido aponta para o banco real do projeto
    Quando o seed roda
    Então os dados demo são gravados no banco demo dedicado e o banco real permanece intacto

  Cenário: resposta demo declara a origem
    Dado o server em modo demo com o seed carregado
    Quando a big picture é consultada
    Então a resposta declara origem demo e traz as métricas da sprint de demonstração

  Cenário: dados reais não carregam aviso de demo
    Dado o server servindo o banco do projeto
    Quando a big picture é consultada
    Então a resposta declara origem live

  Cenário: interface sinaliza dados de demonstração
    Dado a big picture com origem demo
    Quando a interface renderiza a página
    Então um aviso de dados de demonstração fica visível

  Cenário: detalhes do pipeline seguem o idioma da interface
    Dado a visão pipeline de uma spec com commits e amostras registrados
    Quando a interface está em inglês
    Então os estágios e seus detalhes aparecem traduzidos com as contagens corretas
```

## Notas de implementação

- **Isolamento por banco (ADR-019):** `seed.main()` escreve exclusivamente em
  `.specharness/demo.db` (novo `demo_target()`); `seed(target)` mantém a
  assinatura para os testes. `SEED_SPRINT` vira `DEMO-2026-A1` — rótulo
  auto-sinalizante que nunca colide com sprint real.
- **Server:** env `SPECHARNESS_DEMO=1` (setada pelo `just dev`) faz a API
  resolver o banco demo, responder `data_source: "demo"` e defaultar
  `sprint=SEED_SPRINT` na big picture (sem isso o registry real escolheria a
  sprint corrente e as métricas demo sumiriam). Sem a env: `data_source:
  "live"` e banco do ambiente, como hoje.
- **Contrato (ADR-014):** mudanças aditivas — `BigPicture.data_source` e, em
  `PipelineStage`, `detail_key` + `detail_count` + `detail_value` (o `detail`
  pt-BR permanece como fallback). Regenerar `web/openapi.json` com o comando
  do `web/README.md`; `web/src/client` é gerado no build.
- **Web:** banner de demo na big picture quando `data_source === "demo"`;
  `PipelineView` passa a usar as chaves `stage*` já existentes no i18n (hoje
  código morto) e `t(detail_key, {count, value})` com plural do i18next.
- **justfile:** `dev` exporta `SPECHARNESS_DEMO=1`; nova receita `serve` sobe
  o server sem seed e sem a flag, servindo os dados reais.
