---
spec: SPEC-005
title: "Onboarding: conexão LLM obrigatória (provedores via API ou Ollama local)"
status: verifying
type: feature
owner: caio
created: 2026-07-25
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-003]
adrs: [ADR-005, ADR-006]
success_metrics:
  - "specharness llm test valida conectividade e structured output em < 15s por provedor"
  - "Detecção automática de Ollama local em < 2s quando rodando no host"
  - "0 keys em arquivos de config: 100% via variável de ambiente (verificado por teste)"
acceptance:
  - Onboarding exige exatamente uma via funcional - API de provedor OU Ollama - antes de liberar o Readiness Gate
  - specharness llm test executa chamada real com structured output validado por Pydantic e reporta modelo, latência e custo estimado
  - Roteamento por tarefa lê specharness.yaml (default, tasks, fallback)
  - base_url customizada suportada para Azure OpenAI e gateways corporativos
  - Falha em runtime degrada com transparência — funções determinísticas seguem e as semânticas ficam explicitamente pendentes
---

## Contexto

ADR-006: o gate de qualidade é julgamento semântico — parsing sozinho não
sustenta a promessa do produto. A conexão LLM é obrigatória no onboarding,
com Ollama como caminho de custo zero. Porta LLMClient sobre LiteLLM (ADR-005).

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: conexão LLM no onboarding

  Cenário: validação de provedor via API
    Dado que ANTHROPIC_API_KEY está definida no ambiente
    Quando o usuário executa "specharness llm test"
    Então uma chamada real com structured output é validada e o relatório mostra modelo, latência e custo estimado

  Cenário: Ollama local como caminho de custo zero
    Dado que não há key de provedor e o Ollama responde em localhost
    Quando o onboarding detecta provedores disponíveis
    Então o Ollama é oferecido como via principal e o teste executa contra o modelo local

  Cenário: nenhuma via de LLM disponível bloqueia apenas o que é semântico
    Dado que não há key definida nem Ollama acessível
    Quando o usuário tenta avançar no onboarding
    Então o Readiness Gate permanece bloqueado com orientação das duas vias possíveis
    E as funções determinísticas permanecem disponíveis

  Cenário: roteamento por tarefa
    Dado um specharness.yaml com modelo distinto para a tarefa "readiness_gate"
    Quando o gate executa uma avaliação
    Então a chamada usa o modelo configurado para a tarefa e não o default

  Cenário: base_url customizada para gateway corporativo
    Dado que AZURE_OPENAI_API_KEY e AZURE_OPENAI_ENDPOINT estão definidas
    Quando o alvo de LLM é resolvido para o teste
    Então a base_url do endpoint informado é usada na chamada, não a padrão do provedor

  Cenário: fallback quando o provedor principal falha em runtime
    Dado um specharness.yaml cujo default falha e que declara um fallback
    Quando o usuário executa "specharness llm test"
    Então a chamada tenta o fallback e o relatório mostra o modelo de fallback

  Cenário: falha em runtime deixa o semântico explicitamente pendente
    Dado que a única via de LLM falha durante uma avaliação já em andamento
    Quando o gate processa a spec
    Então as funções determinísticas seguem e a camada semântica fica explicitamente pendente, nunca silenciosamente pulada
```
