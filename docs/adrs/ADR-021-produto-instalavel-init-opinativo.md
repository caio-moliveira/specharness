# ADR-021 — specharness como produto instalável: init opinativo, UI embutida, instrumenta o agente

- **Status:** aceita
- **Data:** 2026-07-29
- **Specs relacionadas:** SPEC-001, SPEC-021, SPEC-022, SPEC-023, SPEC-024

## Contexto

Até aqui o specharness é dogfooded como um repositório que se clona e roda. Uma
simulação de primeiro uso (persona TL) expôs o atrito: clonar → instalar `just`
→ subir só a API → descobrir sozinho que o dashboard exige Node e passos fora do
README. O dono do produto definiu a visão-alvo: o specharness deve ser
**instalado como dependência no repo do próprio usuário** (`pip install` /
`uv add`), subir API + Dashboard com um comando, e — via um `init` interativo —
cabear as conexões e **materializar no repo do usuário os arquivos de instrução**
que um coding agent segue. Precisamos fixar o modelo e as decisões de UX antes de
abrir as specs.

## Opções consideradas

1. **Manter "clone + rode" como forma final** — simples de manter, mas o atrito
   de onboarding é alto, não escala para times e não instrumenta o repo *do
   usuário* (só o próprio).
2. **Produto instalável via pacote + init opinativo** — o specharness vira uma
   dependência que cabeia o repo existente do time: conexões no `.env`, config
   no `yaml`, arquivos de instrução do agente gerados, dashboard embutido.

## Decisão

Adotamos a opção 2. O specharness é distribuído como **pacote instalável** e
opera dentro do repo do usuário. Quatro decisões de desenho, alinhadas com o
dono do produto:

1. **Método é espinha fixa; time configura parâmetros.** O `init` nunca oferece
   desligar readiness gate, trailer `Spec:`, BDD travando `done` ou métricas
   anti-vigilância (ADR-006/008/016). Só coleta *parâmetros* (convenção de
   commit, cobertura mínima, projeto do tracker, cadência de sprint, regras de
   PR). A config separa explicitamente "espinha fixa" de "parâmetros do time".
2. **UI embutida, uma porta.** O build do dashboard é compilado no momento de
   gerar o wheel e embutido no pacote; a API monta o estático; `specharness up`
   é um processo numa porta só. Zero Node no lado do usuário.
3. **Init determinístico: presets + profiles.** O `init` compõe os arquivos a
   partir de templates + `profiles/<agente>` (ADR-003/004), preenchidos pelas
   respostas do time. Sem geração livre por LLM no caminho crítico — versionável
   e revisável.
4. **Instrumenta, não orquestra.** O specharness escreve instruções + gates +
   métricas; **não roda o coding agent**. O "de onde o agente puxa o trabalho" é
   declarado nos arquivos gerados (o próximo spec `ready`, derivado do tracker —
   ADR-020); o usuário roda o próprio agente.

Sequenciamento: um **0.x** honesto "clone + rode" (CI verde, getting-started,
Jira) é lançado primeiro para gerar comunidade; o **produto instalável é a
v1.0**.

## Consequências

- Fica mais fácil: o onboarding de um time real (um `init`, uma porta); a tese
  passa a ser medida sobre o repo *do usuário*, não só o nosso.
- Fica mais difícil: o empacotamento (build hook do web no wheel, estático
  montado na API) e a manutenção dos templates de scaffolding por agente.
- Passa a ser obrigatório: **PyPI como caminho principal de distribuição** (não
  mais opcional); as chaves sempre no `.env` do usuário, nunca no `yaml`.
- Passa a ser proibido: o `init` gerar instrução que desligue um gate da espinha
  fixa, ou o specharness assumir o papel de rodar o agente na v1.0.
