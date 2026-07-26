---
spec: SPEC-001
title: "specharness — Documento Fundador"
version: 2.0
status: draft            # draft | approved | ready | in_progress | verifying | done | archived
type: product            # product | feature | architecture | harness
owner: caio
created: 2026-07-25
updated: 2026-07-25
sprint: null
tracker_refs: []
depends_on: []
adrs: [ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008]
success_metrics:
  - "Time-to-first-value (clone → dashboard com dados reais) < 15 min"
  - "Setup de contribuidor (clone → testes verdes) < 10 min"
  - "Primeiro contribuidor externo de harness profile ≤ 3 meses pós-launch"
acceptance:
  - O documento responde o que é o produto, para quem, por que existe e por que agora
  - Todas as decisões de arquitetura estão registradas como ADR com contexto e justificativa
  - O modelo de métricas é fundamentado em pesquisa citada, não em opinião
  - Um contribuidor externo entende o projeto e sabe onde contribuir lendo apenas este documento
---

# specharness

> **Da primeira ideia ao relatório final: a camada de decisão, gestão, qualidade
> e métricas do desenvolvimento orientado a specs na era dos agentes de código.**

---

## Sumário Executivo

Times de tecnologia adotaram agentes de código (Claude Code, Codex, Kimi) e
metodologias spec-driven (Spec Kit, OpenSpec), mas o ciclo de vida do projeto
continua fragmentado — e os dados mostram o custo: o code churn mais que dobrou
desde a adoção em massa de IA, o tempo de review cresceu na casa dos 90%, e
grande parte do ganho de geração é absorvida por retrabalho invisível.

**specharness** é uma plataforma open source e self-hosted que fecha esse ciclo.
O usuário conecta seu próprio ambiente — banco, repositório, gestor de tasks,
agente de código e provedor de LLM — e o specharness passa a operar como camada
de decisão e observação sobre o fluxo que o time já usa:

1. **Antes do código:** garante que nenhuma US/spec chegue ao agente de código
   sem passar por um gate de prontidão (Definition of Ready automatizada,
   avaliada por LLM + checks determinísticos).
2. **Durante o código:** observa commits, PRs e CI; vincula tudo à spec; roda
   BDD como gate de conclusão; coleta métricas objetivas.
3. **Depois do código:** captura a percepção do dev humano sobre o que o agente
   gerou, acompanha a sobrevivência do código em 30/90 dias e devolve tudo
   organizado — dashboard, relatórios de sprint e documentação viva.

A tese do produto, verificável nos dados do próprio time: **specs que entram
prontas produzem código que sobrevive**. O specharness existe para provar essa
correlação — readiness × turnover × percepção — e transformá-la em prática.

---

## 1. Visão e Problema

### 1.1 O problema

O desenvolvimento assistido por agentes criou um paradoxo bem documentado:
nunca foi tão barato gerar código e nunca foi tão caro garantir que ele preste.
Pesquisas independentes convergem nos sintomas (fontes no Apêndice A):

- O code churn — taxa de código recém-escrito que é modificado ou deletado —
  mais que dobrou desde a adoção em massa de assistentes de IA (de ~3.3% para
  ~7.1%).
- O tempo de review cresceu na ordem de 91%, absorvendo o ganho da geração.
- Código de IA passa em todos os testes parecendo limpo e bem comentado, mas
  com problemas estruturais que não viram bug: viram código que um engenheiro
  reescreve em silêncio duas semanas depois.
- Um RCT (METR, 2025) mostrou devs experientes ~19% *mais lentos* com IA
  enquanto acreditavam estar ~20% mais rápidos — um gap de percepção de 39
  pontos que invalida tanto métricas puramente subjetivas quanto a intuição.

Na outra ponta, o ciclo de vida do projeto segue fragmentado: a ideia nasce em
reunião, o PRD vive num Word, ADRs se perdem em threads, o harness do agente é
montado no improviso, as tasks no tracker divergem das specs, e o relatório de
sprint é escrito de memória.

### 1.2 A visão

Uma plataforma que acompanha o projeto inteiro — ideação → discovery →
planning → setup → desenvolvimento → entrega — mantendo a **spec como contrato
central** que liga PRD, work items do tracker, commits, cenários BDD, métricas
e relatórios. O produto apoia a **tomada de decisão** em cada fase: não decide
pelo time, mas estrutura cada decisão, registra o porquê (ADR automático) e
mostra a big picture para todos os papéis.

### 1.3 A tese (e a análise-assinatura)

Se a entrada do agente de código for um contrato validado (spec pronta, BDD
bem escrito, métricas de sucesso mensuráveis), a saída sobrevive mais. O
specharness instrumenta essa hipótese ponta a ponta e entrega ao time a
correlação **readiness score × code turnover × percepção do dev** — o
argumento empírico do spec-driven development, medido no contexto real de cada
time, não em benchmark de laboratório.

### 1.4 Não-objetivos

- **Não é** ferramenta de autoria de spec no repo — Spec Kit, OpenSpec e GSD
  fazem isso bem; nós importamos e interoperamos.
- **Não é** tracker — Redmine, Jira, Azure DevOps e GitHub Issues seguem sendo
  a fonte de tasks; sincronizamos via adapters.
- **Não é** ferramenta de vigilância individual — ver ADR-008.
- **Não é** SaaS na v1 — self-hosted por design; o usuário conecta o próprio
  ambiente e os dados ficam com ele.

---

## 2. Posicionamento e Por Que Agora

### 2.1 As camadas do ecossistema

| Camada | Ferramentas estabelecidas | Papel do specharness |
|---|---|---|
| Autoria de spec no repo | Spec Kit, OpenSpec, GSD (200k+ stars combinadas) | Importers / interoperar |
| Agente de código | Claude Code, Codex, Kimi | Gerar e manter o harness; empacotar o work package |
| Tracker / gestão | Redmine, Jira, Azure DevOps, GitHub, GitLab | Adapter bidirecional |
| Métricas de engenharia | DX, Swarmia, LinearB (proprietárias, genéricas) | Alternativa OSS, centrada em spec + agente |
| **Ciclo de vida SDD: decisão, gate de qualidade, métricas de agente, BDD, relatórios** | **— (gap)** | **É aqui que vivemos** |

### 2.2 Interoperabilidade como estratégia

O público das ferramentas de SDD é o nosso público — como usuários
complementares. A jogada: importar specs do Spec Kit e OpenSpec em vez de pedir
migração. O pitch: *"o DevOps/analytics layer do Spec-Driven Development"*.

### 2.3 Por que agora

Três curvas se cruzaram em 2025–2026: (a) agentes de código viraram o modo
default de trabalho de uma fração relevante dos times; (b) os dados de
qualidade acenderam alerta (churn 2x, review +91%, clones 4x); (c) o mercado de
métricas respondeu com plataformas proprietárias caras e genéricas — nenhuma
centrada na unidade que importa no fluxo com agentes: **a spec**. Não existe
opção open source, self-hosted e spec-céntrica. Essa é a janela.

---

## 3. Personas e Jobs-to-be-Done

| Persona | Job-to-be-done | Lente no produto |
|---|---|---|
| **Sponsor / Gestor** | "Quero saber se o investimento em IA está dando retorno e onde estão os riscos" | Big picture: fase, riscos, métricas agregadas, relatórios |
| **PO** | "Quero que o que foi combinado seja o que foi entregue, e relatórios sem esforço manual" | Ideação, PRD guiado, roadmap, sprints, relatórios |
| **Tech Lead** | "Quero decisões de arquitetura registradas, harness padronizado e um gate que segure US ruim" | Wizards de arquitetura, ADRs, harness, Readiness Gate, gates de CI |
| **Dev** | "Quero receber trabalho pronto pra executar e não ser cobrado por métrica de vaidade" | Suas specs, work packages, cenários BDD, status |
| **Contribuidor OSS** | "Quero um ponto de contribuição claro, pequeno e de impacto" | Adapters, harness profiles, importers — extensão como dados/plug-ins |

Regra de UX transversal: **nada é perguntado duas vezes.** O que o Discovery
capturou (stack, arquitetura, time) alimenta todos os wizards seguintes.

---

## 4. A Jornada — As 6 Fases do Produto

### Fase 1 — Ideação
Captura da ideia: texto livre, notas, transcrição de reunião.
**Output:** problem statement e visão preliminar.
**LLM:** estruturação do texto livre. **Fallback:** formulário manual.

### Fase 2 — Discovery (PO + Tech Lead)
Wizards de decisão guiada: PRD, stack, arquitetura, riscos, não-objetivos.
**Cada decisão relevante gera um ADR automaticamente** — contexto, opções
consideradas, decisão, consequências.
**Output:** PRD versionado + ADRs + perfil do projeto.

### Fase 3 — Planning
Quebra do PRD em specs (autoria própria simplificada **ou** import
Spec Kit / OpenSpec), geração assistida de cenários BDD, definição de métricas
de sucesso por spec, montagem de sprints e **criação/vínculo das tasks no
tracker** via adapter.
**Output:** Spec Registry populado, sprints, work items sincronizados.

### Fase 4 — Setup
Scaffold do repositório (estrutura, convenções, CI) e **geração do harness**
do agente escolhido, seguindo as práticas oficiais do vendor (§10).
**Output:** repo pronto, AGENTS.md + camada específica do runtime.

### Fase 5 — Desenvolvimento
O Quality Loop em operação (§8): Readiness Gate → work package → observação de
commits/PRs/CI → BDD como gate de done → coleta de métricas → percepção do dev
no merge.
**Output:** dashboard vivo da sprint.

### Fase 6 — Entrega
Relatório de sprint (tabular determinístico + narrativa LLM), métricas
atingidas vs. planejadas e **documentação viva** derivada das specs `done` +
estado real do repositório — nunca de promessas.
**Output:** relatório (markdown/docx), documentação publicável, dados de retro.

---

## 5. Onboarding: Conexões como Ponto de Entrada

A primeira experiência do produto não é a ideação — é a **tela de conexões**.
Isso torna o caso brownfield (time com Redmine cheio de US e sprint em
andamento) cidadão de primeira classe, e o greenfield um caso particular.

### 5.1 O wizard de conexões

| # | Conexão | Opções | O que desbloqueia |
|---|---|---|---|
| 1 | **Banco** | SQLite (default, zero-config) ou Postgres próprio (string de conexão) | Persistência |
| 2 | **LLM** ⚠ obrigatória | API key de provedor (Anthropic, OpenAI, Azure OpenAI, ...) **ou** modelo local via Ollama | Readiness Gate, wizards, narrativas |
| 3 | **Repositório** | GitHub, GitLab, Azure Repos | Commits, trailers, PRs, CI status |
| 4 | **Gestor de tasks** | Redmine, Jira, Azure DevOps, GitHub Issues | Import de US/features/epics, sync de status |
| 5 | **Agente de código** | Claude Code, Codex, Kimi | Geração de harness, work packages |

A conexão LLM é **obrigatória** (ADR-006): o gate de qualidade das specs é um
julgamento semântico, e parsing sozinho não sustenta a promessa central do
produto. O onboarding oferece o caminho de custo zero (Ollama local) para quem
não tem ou não quer usar API key, e `specharness llm test` valida a conexão
antes de prosseguir. Cada conexão é testada no ato ("Conectado ✓ — 247 US
importáveis encontradas") e as capacidades desbloqueiam progressivamente: um
time pode operar só com repo + tracker + LLM e adotar harness depois.

### 5.2 Fluxo brownfield

Após conectar o tracker, o import inicial traz US/features/epics como
WorkItems (§6). O time então vincula ou cria specs a partir deles — com
sugestão assistida por LLM ("esta US parece corresponder a estas specs"). A
partir do primeiro commit com trailer, a cadeia inteira se atualiza sozinha.

---

## 6. Modelo de Domínio

Cada tracker tem sua taxonomia (Redmine: issues/versions; Jira:
epics/stories/tasks; Azure DevOps: features/US/tasks). O core define um modelo
canônico e os adapters traduzem (ADR-007):

```
WorkItem (canônico: id, tipo, título, estado, sprint, origem, refs externas)
   ↕ vínculo 1:N ou N:N
Spec (contrato central — §7)
   ↕ trailer "Spec: SPEC-042"
Commit / PullRequest (lidos do repositório conectado)
   ↕ gate
ScenarioRun (execuções BDD no CI: first-run, final)
   ↓
PerceptionSample (micro-survey no merge — §8.4)
MetricSnapshot (série temporal por spec/sprint — §9)
   ↓
Relatórios · Dashboard · Documentação viva
```

Entidades adicionais: `Adr`, `Sprint`, `HarnessProfile`, `Connection`,
`WorkPackage`. Todas as entidades carregam `origin` (nativa, importada,
sincronizada) e referências externas estáveis para reconciliação idempotente
com os sistemas conectados.

---

## 7. O Contrato Central: Spec Schema

### 7.1 Formato

Spec = markdown com frontmatter YAML, ID único, cenários Gherkin embutidos ou
linkados, e métricas de sucesso mensuráveis:

```yaml
---
spec: SPEC-042
title: "Busca por termo exato nas coleções"
status: ready
type: feature
owner: joao
sprint: 2026-S16
tracker_refs: [redmine#1873]
depends_on: [SPEC-038]
adrs: [ADR-012]
success_metrics:
  - "Latência p95 < 800ms"
  - "Zero resultados falso-positivos no conjunto de validação"
acceptance:
  - Busca retorna resultados com o termo exato destacado
  - Resultado cita a fonte do documento
---

## Contexto
...

## Cenários (BDD)

```gherkin
Funcionalidade: busca por termo exato
  Cenário: termo presente em uma coleção
    Dado que a coleção "legislacao" contém o termo "Lei 14.133"
    Quando o usuário busca por "Lei 14.133" no modo exato
    Então o resultado destaca o termo e cita a fonte
```
```

### 7.2 Ciclo de vida

```
draft → approved → ready → in_progress → verifying → done → archived
```

| Transição | Regra |
|---|---|
| `approved → ready` | **Passa no Readiness Gate (§8.1)** — determinístico + LLM |
| `ready → in_progress` | Work item vinculado no tracker; work package gerado |
| `verifying → done` | **Cenários BDD passando no CI** (gate do módulo `verify`) |
| `done → archived` | Congela a spec como documentação histórica |

### 7.3 Convenção de linking commit→spec

Git trailer no corpo do commit — parseável via `git interpret-trailers`, sem
regex frágil:

```
feat: implementa busca por termo exato

Spec: SPEC-042
```

Múltiplas specs = múltiplos trailers. Branch naming
(`spec/SPEC-042-busca-exata`) é convenção recomendada; o trailer é a fonte de
verdade. Commits sem trailer viram métrica ("commits órfãos") e candidatos a
análise semântica por LLM.

### 7.4 Importers

- **OpenSpec:** consome `openspec/specs/` (baseline) e `openspec/changes/`
  (deltas) como specs versionadas.
- **Spec Kit:** mapeia specs por feature, preservando fases specify/plan/tasks.

---

## 8. O Quality Loop

O mecanismo central do produto: garantir qualidade **antes** do agente de
código operar, e medir o resultado **depois** — objetivo e percebido.

### 8.1 Readiness Gate (Definition of Ready automatizada)

Uma spec/US só fica `ready` — disponível para o agente — quando passa por duas
camadas:

**Camada determinística (o piso, sempre roda):**
- Critérios de aceite presentes (≥1) e cenários Gherkin que parseiam
- Mapeamento critério ↔ cenário completo (nenhum critério sem cenário)
- `success_metrics` presentes e sintaticamente mensuráveis
- Dependências (`depends_on`) resolvidas; vínculo com WorkItem existente
- Lint de BDD: estilo declarativo, um `When` por cenário, detecção de termos
  ambíguos não-testáveis ("rápido", "adequado", "amigável")

**Camada LLM (obrigatória — ADR-006):**
Review estruturado com output Pydantic validado, cobrindo o que parsing não
alcança: testabilidade real dos cenários, ambiguidade semântica, contradição
com outras specs e ADRs do projeto, completude frente ao PRD, mensurabilidade
efetiva das métricas de sucesso. Devolve um **readiness score (0–100)** +
issues acionáveis, cada uma com sugestão de correção. O Tech Lead pode
sobrepor o gate (override auditado) — a ferramenta informa, o humano decide.

### 8.2 Work Package

Quando o dev roda `specharness start SPEC-042` (ou clica na UI), o sistema
monta o pacote que o agente de código recebe: a spec validada, os cenários, os
ADRs relevantes, as convenções do projeto e as instruções do harness — no
formato que o runtime escolhido espera. **O agente nunca recebe uma US crua do
tracker; recebe o contrato validado.** Essa é a garantia estrutural de entrada
de qualidade.

### 8.3 Coleta objetiva (pós-geração)

Do git e do CI, sem esforço humano — detalhada no modelo de métricas (§9),
camada 2. Requisito novo e diferenciador: o módulo `track` continua observando
o código **depois do merge** para calcular sobrevivência em 30/90 dias.

### 8.4 Percepção do dev (experience sampling)

Ponto de coleta: o **merge do PR** — o momento em que o humano acabou de
revisar o que o agente gerou. Micro-survey de ~10 segundos (na UI ou como
comentário interativo no PR):

1. Aproveitamento do código gerado (1–5)
2. Retrabalho necessário (nenhum / leve / pesado)
3. Tempo percebido economizado (economizou / neutro / custou tempo)
4. Comentário livre (opcional)

Cada resposta é ancorada à tripla **spec × runtime × modelo**, habilitando a
análise que nenhuma plataforma genérica oferece: percepção humana do
Claude Code vs. Codex vs. Kimi *por tipo de tarefa*, no contexto real do time.
O item 3 cruzado com o cycle time real produz o **gap de percepção** do time —
a métrica revelada pelo RCT da METR, aplicada localmente.

### 8.5 Princípio anti-vigilância (ADR-008)

Todas as métricas medem **o processo, a spec e o agente — nunca o dev
individual**. Agregação mínima: time/sprint. Sem rankings de pessoas, sem
métricas individuais expostas a gestores. Ferramenta que vira vigilância morre
na adoção — e merece morrer. Este princípio é inegociável e está acima de
pedido de feature.

---

## 9. Modelo de Métricas (4 Camadas)

Fundamentado na pesquisa do Apêndice A. Regra de design contra a Lei de
Goodhart: **toda métrica de volume só aparece pareada com uma de qualidade.**

### Camada 1 — Qualidade da entrada
| Métrica | Fonte | Nota |
|---|---|---|
| Readiness score por spec | Gate (§8.1) | A variável independente da tese |
| Issues de readiness por categoria | Gate | Alimenta melhoria de escrita de spec |

### Camada 2 — Resultado objetivo (por spec, automático)
| Métrica | Fonte | Benchmark de referência |
|---|---|---|
| **First-run BDD pass rate** | CI | — (métrica própria; quanto maior, melhor o par spec+agente) |
| Iterações de CI até verde | CI | — |
| **Code turnover 30/90d** | `track` pós-merge | Saudável: <15% (30d); razão IA:humano <1.5x |
| Churn por spec | git | Contexto: média da indústria dobrou pós-IA |
| Ciclos de review no PR | git provider | Tempo de review é onde o ganho de IA se perde (+91%) |
| Cycle time `ready → done` | eventos | Sinal agregado: saudável = queda de 15–30% com IA |
| Commits órfãos / specs órfãs | `track` | Higiene do linking |
| Reopens no tracker | adapter | Proxy de defeito escapado |

**Anti-métricas (não usamos como sucesso):** acceptance rate isolada (mede
clique, não sobrevivência — e alta pode indicar review fraco), LOC, contagem
de commits, story points individuais.

### Camada 3 — Percepção (experience sampling, §8.4)
Aproveitamento, retrabalho percebido, tempo percebido; **gap de percepção** =
tempo percebido × cycle time real.

### Camada 4 — Agregados (sprint/time)
Quadrantes inspirados no DX Core 4 (speed, effectiveness, quality, impact):
velocidade de fluxo (cycle time, throughput de specs), experiência (percepção
agregada + gap), qualidade (turnover, first-run pass, reopens), impacto
(métricas de sucesso das specs atingidas vs. declaradas). Alimenta o relatório
de sprint e o dashboard executivo.

**Análise-assinatura:** correlação readiness × turnover × percepção. Quando o
dashboard mostrar "specs com score ≥ 90 tiveram X% menos turnover e Y× mais
first-run pass", o specharness deixa de ser ferramenta de gestão e vira o
argumento empírico do SDD — eval-driven development aplicado ao processo.

---

## 10. Harness Profiles

O módulo `harness` gera a configuração do agente de código seguindo **as
práticas oficiais do vendor escolhido**. Como essas práticas evoluem rápido,
profiles são **dados versionados, não código** (ADR-004):

```
profiles/
├── claude-code/
│   ├── profile.yaml        # metadados, versão, reviewed_at
│   ├── practices/          # práticas com link para a doc oficial da Anthropic
│   ├── templates/          # CLAUDE.md, skills, hooks, permissions, subagents, MCPs
│   └── checks/             # validações (tamanho, conflitos, anti-patterns)
├── codex/                  # hierarquia AGENTS.md, config — docs da OpenAI
└── kimi/                   # formato e práticas da Moonshot
```

Regras: (1) toda recomendação cita fonte oficial com URL + data — sem fonte,
não entra; (2) profiles com `reviewed_at` antigo exibem aviso de possível
desatualização; (3) o wizard cruza profile × contexto do projeto (stack,
arquitetura, time — já capturados) e gera o harness completo; (4) **AGENTS.md
é sempre a base comum** (padrão aberto da Linux Foundation, suportado por 20+
ferramentas — ADR-003), com a camada específica do runtime por cima;
(5) atualização de profile é o vetor de contribuição OSS por excelência.

---

## 11. Camada de LLM

### Princípios
1. **Conexão obrigatória no onboarding** (ADR-006) — API key ou Ollama local.
2. **BYOK** — keys só via variável de ambiente; nunca em arquivo de config.
3. **Roteamento por tarefa** — tarefas nobres em modelo forte, volume em
   modelo local/barato.
4. **Ollama é cidadão de primeira classe** — detecção automática, prompts
   testados contra modelos menores (evals por tarefa × modelo — §14.2).
5. **Structured outputs sempre** — Pydantic + retry em falha de validação.
6. **Degradação honesta** — sem LLM disponível em runtime (queda de rede,
   quota), funções determinísticas seguem operando e as semânticas ficam
   explicitamente pendentes, nunca silenciosamente puladas.

### Configuração (`specharness.yaml`)

```yaml
llm:
  default: anthropic/claude-sonnet-4-6
  tasks:
    readiness_gate: anthropic/claude-sonnet-4-6   # a tarefa mais crítica
    report: anthropic/claude-sonnet-4-6
    harness: openai/gpt-5.6
    commit_analysis: ollama/qwen3:8b              # volume → local/barato
  fallback: ollama/llama3.3
  base_url: null            # Azure OpenAI / gateways corporativos
```

Requisitos transversais: `specharness llm test` (valida conectividade), cache
por hash de input, custo visível (tokens/execução + budget cap), `--dry-run`,
observabilidade opcional (Langfuse/OpenTelemetry, off por default) e
**privacidade documentada por tarefa** — o que sai da máquina e para onde
(requisito eliminatório em governo e redes fechadas).

Nota de produto: há **dois consumidores de LLM** — o specharness (gate,
wizards, relatórios) e o agente de código do time (configurado pelo harness).
Configs separadas, explícitas na UI.

---

## 12. Arquitetura de Software

### 12.1 Stack

- **Backend/CLI:** Python 3.11+ · FastAPI · Typer · SQLAlchemy 2 + Alembic ·
  Pydantic v2 · LiteLLM (sob interface própria — ADR-005)
- **Frontend:** React + TypeScript strict · Vite · Vitest · Testing Library
- **Storage:** SQLite (default) · Postgres (opcional) — mesma camada
  SQLAlchemy (ADR-002)
- **Deploy:** clone + `uv sync` + `specharness up`; Docker Compose opcional

### 12.2 Estilo arquitetural: ports & adapters

O `core` define o domínio e as portas (interfaces); tudo que toca o mundo
externo é adapter registrado por entry points (ADR-001). Consequências:
contribuidor cria adapter novo sem tocar no core; core testável sem rede; e o
mesmo domínio serve CLI, API e daemon.

```
specharness/
├── packages/
│   ├── core/               # domínio, portas, Spec Registry, parser, gate
│   ├── server/             # FastAPI (API do web app + webhooks)
│   ├── web/                # React: dashboard, wizards, conexões
│   ├── cli/                # Typer: init, connect, harness, start, track,
│   │                       #        verify, report, llm, up
│   ├── adapters/
│   │   ├── trackers/       # redmine, jira, azure-devops, github, gitlab
│   │   ├── git/            # github, gitlab, azure-repos
│   │   ├── llm/            # LLMClient sobre LiteLLM
│   │   └── importers/      # openspec, spec-kit
│   ├── profiles/           # harness profiles (dados)
│   └── metrics/            # snapshots, séries, queries
├── specs/                  # dogfooding: as specs do próprio specharness
├── docs/                   # MkDocs Material
└── .github/                # CI, templates, release
```

### 12.3 Ingestão de eventos

Duas vias equivalentes, mesma pipeline de processamento: **webhooks** (push,
PR, CI status — para self-hosted com rede aberta) e **polling/GitHub Action**
(para ambientes fechados). Processamento idempotente por chave natural
(commit SHA, PR id, run id) — reprocessar nunca duplica métricas.

### 12.4 Dados e migração

Alembic para migrações desde o commit 1. Snapshots de métricas são
imutáveis e append-only (série temporal); estado derivável é recalculável a
partir dos eventos — permite corrigir bugs de cálculo retroativamente.

### 12.5 Segurança e privacidade

Credenciais de conexões cifradas em repouso (chave local do usuário); tokens
com escopo mínimo documentado por adapter; nenhum dado sai do ambiente exceto
chamadas LLM explicitamente configuradas (documentadas por tarefa — §11);
SECURITY.md com política de report; dependências monitoradas (Renovate).

---

## 13. Registro de Decisões (ADRs Fundadores)

| ADR | Decisão | Contexto → Justificativa | Consequências |
|---|---|---|---|
| **001** | Formato canônico primeiro, adapters depois (ports & adapters) | Múltiplos trackers/runtimes/provedores com taxonomias próprias | Core sem dependência externa; contribuição por plug-in; custo: camada de tradução |
| **002** | SQLite default, Postgres opcional, via SQLAlchemy | Adoção exige zero-infra; times precisam escalar | Um só ORM; sem features exclusivas de Postgres no caminho crítico |
| **003** | AGENTS.md como base do harness + camada por runtime | Padrão aberto (Linux Foundation), 60k+ repos, 20+ ferramentas | Harness portável; camadas vendor-specific isoladas nos profiles |
| **004** | Harness profiles como dados versionados, não código | Práticas dos vendors mudam a cada poucos meses | Comunidade atualiza sem tocar no core; exige disciplina de citação de fonte |
| **005** | LiteLLM sob interface própria `LLMClient` | Ecossistema inteiro de provedores vs. custo de manter SDKs | Troca de camada possível sem tocar no domínio; dependência pesada aceita |
| **006** | **Conexão LLM obrigatória; gate de qualidade é LLM-first** | Testabilidade/ambiguidade são julgamentos semânticos; parsing só não sustenta a promessa central. Ollama garante caminho de custo zero | Onboarding exige provedor ou Ollama; checks determinísticos são o piso; degradação honesta em runtime (§11) |
| **007** | Modelo canônico WorkItem no core; adapters traduzem taxonomias | Redmine/Jira/AzDO têm hierarquias incompatíveis | Vínculo Spec↔WorkItem uniforme; brownfield first-class; custo: mapeamentos por adapter |
| **008** | Métricas medem processo/spec/agente — nunca o indivíduo | Vigilância mata adoção e corrompe as métricas (Goodhart) | Agregação mínima time/sprint; sem rankings; princípio acima de feature request |

Formato completo de cada ADR (contexto, opções consideradas, decisão,
consequências) vive em `docs/adrs/` — a tabela é o índice.

---

## 14. Engenharia do Próprio Projeto (SDLC)

### 14.1 Dogfooding

O specharness é desenvolvido com specs dele mesmo em `specs/`, com trailers
nos commits, BDD como gate e relatórios de sprint publicados. É a melhor
documentação, a melhor demo e o primeiro estudo de caso da tese.

### 14.2 Estratégia de testes

- **Pirâmide:** unit no core (portas mockadas) → contract tests por adapter
  (cada adapter contra gravações reais da API do serviço) → E2E fino via CLI.
- **BDD:** os cenários das nossas próprias specs rodam como gate — o módulo
  `verify` testa a si mesmo.
- **Evals de prompt:** cada tarefa LLM (readiness gate, narrativa de
  relatório, sugestão de vínculo) tem golden dataset versionado e roda em CI
  contra os modelos suportados — incluindo os locais pequenos. Mudança de
  prompt sem eval passando não mergeia. (Eval-Driven Development aplicado ao
  próprio produto.)
- **Cobertura:** ≥85% no core; badge no README.

### 14.3 Definition of Ready / Done (nossas)

- **Ready:** a spec passa no nosso próprio Readiness Gate.
- **Done:** BDD verde no CI + docs atualizadas + eval de prompt verde (quando
  toca LLM) + changelog entry via Conventional Commits.

### 14.4 CI/CD

Pipeline em todo PR (<5 min): Ruff + pyright strict (core) + pytest (matrix
3.11/3.12/3.13) + ESLint/Prettier + Vitest + build. Release automatizada:
Conventional Commits → release-please → tag → PyPI (trusted publishing) + npm
+ changelog. pre-commit versionado no repo.

---

## 15. Open Source: Governança, Comunidade e Crescimento

### 15.1 Fundação

Apache 2.0 (proteção de patente; padrão no ecossistema de IA) · Contributor
Covenant · SECURITY.md · SemVer · roadmap público (GitHub Projects) · GitHub
Discussions · docs em MkDocs Material com quickstart de 5 minutos + demo.

### 15.2 Experiência do contribuidor

Meta: clone → `uv sync` → `pre-commit install` → testes verdes em **<10 min**.
Templates de issue/PR; `good first issue` desde o dia 1 — começando pelos
harness profiles ("as práticas do vendor X mudaram" é a porta de entrada
perfeita: pequena, de impacto, sem tocar no core). Escada de contribuição:
profile → adapter → importer → core.

### 15.3 Estratégia de crescimento (a ambição 200k)

Sem ilusão: 200k stars é território de fenômeno (o *combinado* de Spec Kit +
OpenSpec + GSD). O caminho é composto por motores que se reforçam:

1. **Time-to-value brutal:** o critério de release da Fase A (<15 min até
   dashboard com dados reais) é a feature de marketing nº 1.
2. **Dogfooding público:** nossos relatórios de sprint e métricas publicados —
   o repo é a demo.
3. **Conteúdo como distribuição:** a análise readiness × turnover × percepção
   gera os artigos/talks que a comunidade de engenharia quer ler agora
   ("nossos dados de 6 meses medindo Claude Code vs. Codex por tipo de
   tarefa"). Curso e workshops do mantenedor como canal já existente.
4. **Interoperabilidade como aliança:** importers de OpenSpec/Spec Kit +
   PRs de integração nas docs deles; pegar carona nos 200k, não competir.
5. **Comunidade BR como base de lançamento** e i18n (UI em inglês, pt-BR como
   primeira tradução) para o alcance global.
6. **Marcos de credibilidade:** benchmark público de harness profiles,
   apresentação em eventos de engenharia de software e IA, case de órgão
   público (adoção self-hosted em rede fechada — nicho mal servido
   globalmente).

### 15.4 Governança de longo prazo

Mantenedor único no início com decisões via ADR público; a partir de 3
mantenedores ativos, RFC process leve para mudanças de contrato (spec schema,
portas do core). Profiles têm codeowners próprios — caminho de promoção para
contribuidores recorrentes.

---

## 16. Roadmap

### Fase A — Fundação (MVP, primeiro release público)
- `core`: Spec Registry + schema + parser + ciclo de vida + Readiness Gate
  (determinístico + LLM)
- Onboarding de conexões: SQLite/Postgres, LLM (provedores + Ollama), GitHub,
  Redmine + GitHub Issues
- `track`: linking por trailer, métricas camadas 1–2 (incluindo turnover
  30/90d), commits/specs órfãos
- `verify`: cenários Gherkin como gate de CI
- `report`: relatório de sprint (tabular + narrativa LLM)
- Micro-survey de percepção no merge (camada 3)
- Web: onboarding + dashboard da big picture + visão pipeline por spec

**Critério de release:** um time brownfield conecta repo real + tracker real +
LLM e obtém dashboard com métricas e relatório de sprint em **<15 minutos**.

### Fase B — Decisão e Setup
- Wizards de Discovery (PRD, stack, arquitetura → ADRs automáticos)
- `harness` com profile Claude Code completo + work packages
- Importer OpenSpec · Adapter Jira
- Web: wizards interativos, edição de specs, Agent Analytics (camada 4)

### Fase C — Ciclo completo
- Profiles Codex e Kimi · Importer Spec Kit · Adapters Azure DevOps, GitLab
- Documentação viva (Fase 6 completa)
- Análise semântica de commits órfãos · análise-assinatura
  (readiness × turnover × percepção) no dashboard executivo

---

## 17. Métricas de Sucesso do Projeto

| Métrica | Alvo |
|---|---|
| Time-to-first-value (conexões → dashboard real) | < 15 min |
| Setup de contribuidor (clone → testes verdes) | < 10 min |
| Cobertura de testes no core | ≥ 85% |
| Specs próprias `done` com BDD passando | 100% |
| Evals de prompt verdes em CI para todos os modelos suportados | 100% |
| Primeiro contribuidor externo de harness profile | ≤ 3 meses pós-launch |
| Primeiro case público de time usando a análise-assinatura | ≤ 6 meses pós-launch |

---

## 18. Riscos e Mitigações

| Risco | Prob. | Impacto | Mitigação |
|---|---|---|---|
| Vendors mudam formatos de harness rápido demais | Alta | Médio | ADR-004 (profiles como dados) + `reviewed_at` + comunidade |
| Gate LLM com falsos positivos irrita times | Média | Alto | Override auditado do Tech Lead; evals de prompt; score, não veto binário |
| Custo de LLM afasta adoção | Média | Alto | Ollama first-class; roteamento por tarefa; cache; budget cap |
| Times percebem métricas como vigilância | Média | Crítico | ADR-008 inegociável + comunicação explícita na UI e docs |
| Scope creep (produto tenta ser tracker/SDD tool) | Alta | Alto | Não-objetivos (§1.4) revisados a cada release |
| APIs de trackers instáveis/limitadas (Redmine plugins, rate limits) | Média | Médio | Contract tests por adapter; polling degradado; cache |
| Fadiga do micro-survey | Média | Médio | 3 itens, 10 segundos, skippável; amostragem configurável |

---

## 19. Questões em Aberto

1. Auth do web app multiusuário (Fase B): local simples vs. OIDC opcional.
2. Métricas históricas em times sem Postgres: SQLite commitado, artefato de
   CI ou branch dedicada.
3. Daemon `track` contínuo vs. modo GitHub Action puro como default.
4. Nome e formato do work package (arquivo? MCP? ambos?) por runtime.

---

## Apêndice A — Referências da Pesquisa de Métricas

- **GitClear** — análises longitudinais de churn (3.3% → 5.7–7.1% pós-adoção
  de IA) e crescimento de código clonado/duplicado.
- **Code Turnover Rate** (Larridin, Developer Productivity Hub, 2026) —
  definição, benchmarks (<15% em 30d; razão IA:humano <1.5x; média da
  indústria 1.8–2.5x) e distinção churn × turnover.
- **Faros AI** — aumento de ~91% no tempo de review com adoção de IA.
- **METR (2025)** — RCT: devs experientes ~19% mais lentos com IA acreditando
  estar ~20% mais rápidos (gap de percepção de 39 pontos).
- **DX Core 4** (getdx.com) — framework unificando DORA, SPACE e DevEx em
  speed/effectiveness/quality/impact; coleta por sistema + survey +
  experience sampling.
- **arXiv 2507.15003** — PR acceptance de agentes autônomos 15–40 p.p. abaixo
  de humanos em feature/fix/perf, contrastando com benchmarks de laboratório.
- **amux.io (2026)** — acceptance rate como métrica de vaidade; cycle time
  como sinal agregado (saudável: −15–30%).
- **AGENTS.md / Agentic AI Foundation (Linux Foundation)** — padrão aberto de
  instrução de agentes, 60k+ repos, 20+ ferramentas.

*(URLs completas em `docs/references.md` no repositório.)*
