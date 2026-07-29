---
spec: SPEC-021
title: "Distribuição PyPI e boot único: pip install + specharness up"
status: in_progress
type: feature
owner: caio
created: 2026-07-29
sprint: 2026-C1
tracker_refs: []
depends_on: [SPEC-016]
adrs: [ADR-021, ADR-013, ADR-014]
success_metrics:
  - "pip install specharness num venv limpo expõe o comando `specharness` em < 60s, sem Node instalado"
  - "specharness up serve API e dashboard na MESMA porta; GET / responde 200 com o dashboard, não 404"
  - "O wheel embute o dashboard compilado; nenhum passo de npm roda na instalação do usuário (assert de conteúdo do artefato)"
  - "0 segredos ou arquivos de desenvolvimento presentes no sdist/wheel (assert de conteúdo do artefato)"
acceptance:
  - Um pip install specharness num ambiente limpo instala o CLI e todas as dependências de runtime
  - specharness up sobe a API e o dashboard num único processo e numa única porta
  - A raiz (GET /) serve o dashboard e as rotas /api e /docs continuam funcionando
  - O dashboard compilado vai embutido no wheel como package data, sem exigir Node no usuário
  - O artefato publicável não contém segredos nem arquivos de desenvolvimento
  - specharness up sem banco configurado encerra com erro acionável orientando o init, sem stack trace
---

## Contexto

Primeira spec da v1.0 (ADR-021): tornar o specharness um pacote instalável. Hoje
o produto exige clonar o repo, instalar `just` e subir API e web separadamente —
a simulação de primeiro uso expôs o atrito (raiz em 404, dashboard exigindo Node
e passos fora do README). O alvo é `pip install specharness` (ou `uv add`)
seguido de um único `specharness up` que serve API + dashboard numa porta só.

Decisões de empacotamento (a fechar no readiness):

- A distribuição pública é `specharness`; o workspace interno permanece
  `specharness-workspace`. O comando de console `specharness` já existe (Typer).
- O build do web (Vite → `dist/`) roda ao gerar o wheel, via build hook, e o
  `dist/` entra como package data. Em runtime a API monta o estático com fallback
  de SPA (index.html para rotas não-/api), e `GET /` passa a servir o dashboard.
- `specharness up` faz o boot do servidor servindo o estático; a semântica de
  *live por padrão vs demo* é da SPEC-024. Aqui basta que `up` suba e sirva.
- **Node é requisito de build-time** (compilar o dashboard para o wheel), no
  ambiente de release/CI. O runtime do usuário nunca precisa de Node.

## Fora de escopo

- Publicar de fato no PyPI (é passo de release) — aqui o alvo é o artefato
  construível e instalável, validado localmente / TestPyPI.
- Empacotar como container Docker — pode vir depois, não é o caminho principal.
- O default live vs demo do dashboard — é a SPEC-024.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: instalação e boot único do specharness

  Cenário: instalação limpa expõe o comando
    Dado um ambiente virtual limpo sem Node instalado
    Quando o pacote specharness é instalado a partir do wheel
    Então o comando specharness fica disponível com todas as dependências de runtime

  Cenário: um comando sobe API e dashboard na mesma porta
    Dado o specharness instalado e um banco configurado
    Quando o usuário roda specharness up
    Então a API responde em /api e /docs e o dashboard é servido na raiz, na mesma porta

  Cenário: o dashboard vem embutido, sem build no usuário
    Dado o wheel publicável do specharness
    Quando seu conteúdo é inspecionado
    Então o dashboard compilado está incluído como package data e nenhum passo de npm é exigido na instalação

  Cenário: o artefato não vaza segredos nem arquivos de dev
    Dado o sdist e o wheel gerados
    Quando seu conteúdo é inspecionado
    Então nenhum arquivo .env, chave ou artefato de desenvolvimento está presente

  Cenário: boot sem banco configurado falha com orientação
    Dado o specharness instalado num repositório sem configuração de banco
    Quando o usuário roda specharness up
    Então o comando encerra com erro acionável orientando rodar o init, sem stack trace
```
