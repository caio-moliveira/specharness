---
spec: SPEC-014
title: "Percepção do dev: micro-survey no merge (experience sampling)"
status: verifying
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A4
tracker_refs: []
depends_on: [SPEC-006, SPEC-009]
adrs: [ADR-008]
success_metrics:
  - "Tempo de resposta do survey <= 15s no percurso completo (medido em teste de usabilidade)"
  - "Taxa de resposta >= 60% dos merges elegíveis no dogfooding do próprio specharness"
  - "100% das amostras ancoradas à tripla spec x runtime x modelo"
acceptance:
  - No merge de PR vinculado a spec, o dev responde 3 itens - aproveitamento (1-5), retrabalho (nenhum/leve/pesado), tempo percebido (economizou/neutro/custou) - e comentário livre opcional
  - Survey é skippável; skip é registrado sem penalidade e sem re-prompt no mesmo PR
  - Amostra é ancorada a spec, runtime e modelo usados na implementação
  - Gap de percepção da sprint = tempo percebido agregado x cycle time real
  - Nenhuma resposta individual é exposta; apenas agregados por sprint/time
---

## Contexto

A camada 3 (SPEC-001 §8.4): o RCT da METR mostrou que percepção sozinha mente
e sistema sozinho não explica — o valor está no cruzamento. O merge é o
momento em que o humano acabou de revisar o que o agente gerou.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: micro-survey de percepção no merge

  Cenário: coleta ancorada no merge
    Dado um PR vinculado à SPEC-042 implementada com Claude Code
    Quando o PR é mergeado e o dev responde o survey
    Então a amostra fica ancorada à tripla spec, runtime e modelo

  Cenário: skip é respeitado
    Dado um dev que optou por pular o survey de um PR
    Quando o registro é processado
    Então o skip é armazenado e nenhum novo prompt ocorre para o mesmo PR

  Cenário: gap de percepção calculado na sprint
    Dado amostras de tempo percebido e cycle times reais de uma sprint
    Quando o agregado da sprint é calculado
    Então o gap de percepção compara o percebido com o medido

  Cenário: resposta individual não é exposta
    Dado amostras de percepção coletadas de três devs
    Quando o dashboard exibe a sprint
    Então apenas agregados aparecem, sem identificação de respondente

  Cenário: PR sem spec vinculada não coleta
    Dado um PR sem nenhuma spec vinculada e sem spec informada
    Quando o survey é acionado
    Então a coleta é recusada com orientação e nenhuma amostra é registrada

  Cenário: item fora do domínio é rejeitado
    Dado uma resposta com aproveitamento fora da faixa de 1 a 5
    Quando o registro é processado
    Então a amostra é rejeitada e nada é persistido
```

## Notas de implementação

Escopo fechado no readiness (2026-07-27). Decisões:

- **Coleta via CLI, não web.** O specharness é um CLI; não há camada de input web
  (o dashboard da SPEC-016 é read-only). O comando `specharness survey` registra a
  resposta (ou o skip) de uma PR, não-interativo por flags — análogo a `verify`/
  `metrics`. Idempotente por PR: existindo resposta ou skip, não há novo prompt
  (acceptance[2]).
- **Tripla spec × runtime × modelo (acceptance[3]) por inputs explícitos.** O comando
  recebe `--runtime` e `--model`; o spec é derivado do vínculo da PR (SPEC-009) e pode
  ser sobrescrito por `--spec`. Sem PR vinculada nem `--spec`, a coleta é recusada.
- **Gap de percepção (acceptance[4]) = divergência de direção.** `tempo_percebido`
  vira direção {economizou:-1, neutro:0, custou:+1}; o cycle time da spec (SPEC-013)
  vira direção pela posição relativa à mediana da sprint (abaixo=−1 rápido,
  acima=+1 lento). O gap da sprint = proporção de amostras cuja direção percebida
  diverge da medida — número em [0,1]. Amostras sem cycle time conhecido não entram.
- **Privacidade por construção (ADR-008).** A amostra é ancorada a PR/spec/runtime/
  modelo — a identidade do respondente **nunca é armazenada**. O agregado da sprint
  só expõe contagens e distribuições; não há por onde vazar um indivíduo.
- **Núcleo puro vs. adapter (ADR-001).** Validação dos itens, direções e cálculo do
  gap e dos agregados são core puro; a persistência das amostras e a leitura dos
  cycle times (do snapshot da SPEC-013) são adapter.
