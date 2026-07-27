---
spec: SPEC-004
title: "Onboarding: conexão de banco (SQLite default, Postgres opcional)"
status: in_progress
type: feature
owner: caio
created: 2026-07-25
updated: 2026-07-26
sprint: 2026-A1
tracker_refs: []
depends_on: [SPEC-003]
adrs: [ADR-001, ADR-002, ADR-010]
success_metrics:
  - "Caminho default: 0 prompts interativos — `specharness connect db` completa com stdin fechado e exit code 0 (teste `test_default_path_never_prompts`)"
  - "A mesma suíte de contrato de banco passa contra SQLite e Postgres sem uma linha de código diferente — só SPECHARNESS_DATABASE_URL (job `test` do CI roda as duas)"
  - "`alembic upgrade head` do zero em < 10s nos dois bancos, medido com perf_counter no teste, não afirmado"
  - "Cobertura de `specharness_adapters.db` >= 90% (`just cov-db`), sem `# pragma: no cover` em caminho exigido por critério de aceite"
  - "Toda classe de falha de conexão tem teste que asserta a substring acionável E a ausência da senha na mensagem"
acceptance:
  - Sem configuração, `specharness connect db` cria e migra um SQLite local sem nenhum prompt
  - Com SPECHARNESS_DATABASE_URL apontando para um Postgres acessível, conecta, valida e migra nesse banco
  - alembic upgrade head é idempotente - a segunda execução é no-op e sai 0, nos dois bancos
  - Falha de conexão gera erro em português nomeando SPECHARNESS_DATABASE_URL e a classe da falha
  - URL malformada ou driver não suportado é rejeitada antes de qualquer tentativa de I/O
  - Nenhuma mensagem de erro expõe a senha presente na URL de conexão
  - O core não importa SQLAlchemy - a porta vive no core, a implementação vive em adapters
---

## Contexto

Primeira conexão do onboarding (SPEC-001 §5.1). Zero-infra por default é
requisito de adoção; Postgres próprio é requisito de time (ADR-002). Models
únicos SQLAlchemy 2 servem async (server) e sync (CLI) — ADR-010.

Esta spec é a primeira que introduz I/O no projeto, então ela carrega o ônus
de provar que a fronteira do ADR-001 sobrevive ao contato com um ORM.

## Cenários (BDD)

```gherkin
# language: pt
Funcionalidade: conexão de banco no onboarding

  Cenário: caminho default cria SQLite sem perguntas
    Dado que nenhuma variável de banco está definida e stdin está fechado
    Quando o usuário executa "specharness connect db"
    Então um SQLite é criado em ".specharness/specharness.db", migrado até head, e o comando sai 0

  Cenário: usuário conecta seu próprio Postgres
    Dado que SPECHARNESS_DATABASE_URL aponta para um Postgres acessível
    Quando o usuário executa "specharness connect db"
    Então a conexão é validada, as migrações são aplicadas nesse banco, e nenhum SQLite é criado

  Cenário: segunda migração é no-op
    Dado um banco já migrado até head
    Quando "alembic upgrade head" roda uma segunda vez
    Então nenhuma migração nova é aplicada, a revisão continua a mesma, e o comando sai 0

  Esquema do Cenário: falha de conexão orienta o usuário
    Dado que SPECHARNESS_DATABASE_URL provoca a falha "<falha>"
    Quando o onboarding testa a conexão
    Então o erro em português menciona "SPECHARNESS_DATABASE_URL" e "<substring>"

    Exemplos:
      | falha                  | substring                |
      | host inacessível       | não foi possível conectar |
      | autenticação recusada  | autenticação             |
      | banco inexistente      | banco de dados não existe |
      | driver ausente         | driver                   |

  Cenário: URL malformada é rejeitada antes de qualquer I/O
    Dado que SPECHARNESS_DATABASE_URL contém um esquema não suportado "mysql://x/y"
    Quando o onboarding testa a conexão
    Então o erro menciona "URL inválida" e nenhuma tentativa de conexão de rede é feita

  Cenário: senha nunca aparece na mensagem de erro
    Dado que SPECHARNESS_DATABASE_URL contém a senha "s3nh4-secreta" e um host inacessível
    Quando o onboarding testa a conexão
    Então a mensagem de erro não contém "s3nh4-secreta" em nenhuma forma

  Cenário: core permanece livre de SQLAlchemy
    Dado o pacote specharness_core importado isoladamente
    Quando os módulos do core são varridos por imports de framework
    Então nenhum módulo do core importa sqlalchemy, alembic ou driver de banco
```

## Decisões de escopo

Registradas no readiness review de 2026-07-26, antes da implementação. As três
primeiras existem porque o texto original da spec não as fixava, e duas pessoas
lendo-o implementariam coisas diferentes.

**E1 — A porta vive no core, a implementação vive em adapters.**
SQLAlchemy e Alembic são I/O; `packages/core` é domínio puro (ADR-001, zero
imports de framework). O core define o protocolo; `specharness_adapters.db`
implementa com SQLAlchemy 2, models declarativos únicos e engines async/sync
sobre eles (ADR-010). O critério de aceite 7 e o último cenário existem para
que essa fronteira seja *testada*, não apenas prometida — a próxima spec que
precisar de persistência vai encontrar a porta pronta, e não um import de
SQLAlchemy no domínio.

**E2 — O SQLite default mora em `.specharness/specharness.db`, relativo à raiz
do projeto.** O specharness é uma ferramenta com escopo de repositório: ela já
lê `specs/` e o git local. Um banco per-repo é o que casa com isso, e mantém o
"zero perguntas" honesto (nada de escolher diretório). Diretório XDG global
foi descartado: dois repositórios compartilhariam métricas de specs diferentes.

**E3 — Postgres roda no CI via service container.**
"Migrações testadas nos dois" (ADR-002, Consequências) só é auditável se as
duas metades rodarem. O job `test` do `pr.yaml` ganha um service `postgres:16`
e roda a suíte de contrato duas vezes — SQLite e Postgres. A alternativa
(marker que faz skip sem URL) foi descartada porque deixaria os critérios 2 e 3
verdes com a metade Postgres nunca executada, exatamente o tipo de evidência
vazia que o ADR-016 existe para impedir. `.github/workflows/` exige confirmação
humana; a mudança está no escopo aprovado desta spec.

**E4 — A senha sai da mensagem, não só do log.**
O critério 6 não estava na spec original. Entrou porque esta é a única feature
do produto que manipula credencial em texto plano, e uma URL de Postgres com
senha vazando num traceback de CI é um incidente real, barato de prevenir e
barato de testar.

**E5 — As classes de falha são enumeradas, não descritas.**
O texto original pedia "a causa provável", que não é verificável por máquina.
Trocado pelo padrão que a SPEC-003 estabeleceu: cada classe de falha tem uma
substring acionável e assertável. Falhas fora das quatro classes caem num
default que ainda nomeia a env var — o que a spec proíbe é a mensagem genérica
sem ponteiro, não a existência de um catch-all.

## Decisões e desvios da implementação

**D1 — Classificação prefere SQLSTATE ao texto do driver.**
Os cenários pedem substrings em português na mensagem *que o usuário lê*; a
decisão de qual classe aplicar vem do SQLSTATE (28P01, 3D000, 08001/04/06),
que é contrato do Postgres. O texto do driver é fallback, porque muda com
locale, versão e plataforma — e um teste que dependa dele quebra sozinho num
runner com locale diferente.

Consequência deliberada: o texto do driver **nunca é ecoado** ao usuário. Um
driver é livre para incluir a connection string inteira no que levanta, e o
critério 6 não sobreviveria a repassá-la. O que sai da classificação é o nome
da classe da exceção original (`OperationalError`), que não pode carregar
segredo, mais a URL já redigida.

**D2 — A redação da senha reconstrói a URL, não faz replace.**
`redact_password` remonta a URL a partir das partes parseadas, então nem a
forma plana nem a percent-encoded do segredo sobrevive. Um `str.replace` da
senha deixaria passar `p%40ss` quando a senha é `p@ss`. Testado com senhas que
codificam diferente. A função também não levanta para entrada inparseável:
uma rede de segurança que estoura é pior do que nenhuma.

A redação cobre **dois** portadores de senha, não um: o userinfo
(`user:senha@host`) e os parâmetros de conexão que o libpq lê como senha
(`?password=`, `sslpassword`, e apelidos). A verificação independente (ADR-016)
achou que a versão original só cobria o userinfo — uma URL de Postgres
gerenciado com `?password=...` vazava o segredo inteiro na mensagem de erro,
violando o critério 6. Corrigido reconstruindo também a query com os
parâmetros de senha redigidos, travado por teste de unidade (cada chave de
senha) e por teste ponta a ponta pelo gateway. Colchetes de literal IPv6 na
URL redigida também passaram a ser reconstruídos, para que a URL exibida
continue válida.

**D3 — `sqlite://` explícito é aceito, embora nenhum critério exija.**
Rejeitar uma URL SQLite válida seria surpreendente, e é o mesmo dialeto que a
ferramenta já fala. Custa três linhas e tem teste. `is_default` fica `False`:
o usuário configurou algo, mesmo que tenha configurado SQLite.

**D4 — Env var vazia é ausência de configuração, não configuração inválida.**
`SPECHARNESS_DATABASE_URL=""` cai no caminho default. Um shell que exporta a
variável vazia é comum demais para tratar como erro.

**D5 — O harness de teste tem a própria variável.**
`SPECHARNESS_TEST_POSTGRES_URL` diz onde vive o Postgres *dos testes*. Ela
existe porque os casos SQLite precisam continuar rodando na mesma sessão — se
o Postgres viesse por `SPECHARNESS_DATABASE_URL`, o caminho default nunca
seria exercitado. O **produto** continua conhecendo uma única variável, que é
o que a métrica 2 promete.

**D6 — Dois defeitos achados pelos próprios testes, não por revisão.**

1. *`current_revision` não criava o diretório do SQLite.* Num caminho default
   virgem, `.specharness/` não existe, e o sqlite3 reporta diretório ausente
   como "unable to open database file" — que a classificação, corretamente,
   lia como `DatabaseNotFound`. O usuário receberia "o banco de dados não
   existe" apontando para um problema que ele não tem. `migrate()` mascarava
   isso porque já chamava `ensure_storage`.
2. *O tratamento de erro do `command.upgrade` não tinha teste.* Ao escrever o
   caso que faltava (banco alcançável, migração impossível por tabela
   colidente) ficou claro que a cláusula `except DatabaseError: raise` era
   código morto — nada dentro do Alembic levanta erro nosso. Removida.

**D7 — `# pragma: no cover` usados, e por quê.**
A métrica 4 proíbe pragma em caminho exigido por critério de aceite. Os dois
usos não são: o guard de `after is None` em `migrate()` é estreitamento de
tipo para um estado que o Alembic não produz, e o ramo offline do `env.py` só
roda sob `alembic -x offline`, que nenhum critério cobre. Registrados aqui
para serem escopo declarado.

**D8 — Follow-ups aceitos, não fechados nesta entrega.**

1. *`?sslmode=require` não é traduzido para asyncpg.* A query string é
   preservada verbatim, e asyncpg usa `ssl=` em vez de `sslmode=`. Um usuário
   com Postgres gerenciado (que costuma exigir TLS) veria a engine async
   falhar onde a sync funciona. Nenhum critério cobre TLS; entra na spec que
   ligar o server de fato.
2. *A porta não tem Repository nem UnitOfWork.* Decisão E-b da gap analysis:
   sem consumidor, o desenho erra. SPEC-009 e SPEC-013 desenham com o caso de
   uso na mão.
3. *`just cov-db` roda só com SQLite no job `test-integrity`.* O gate de 90%
   é medido sem Postgres; a metade Postgres tem cobertura só no job `test`,
   que não tem gate de cobertura do adapter.
4. *`uv run` nos hooks do pre-commit re-resolve o `uv.lock`.* Commitar um
   `pyproject.toml` de workspace sem o lock faz o hook reescrever um arquivo
   staged e abortar o commit, com os arquivos vazando para o commit seguinte.
   Aconteceu nesta entrega e foi corrigido no histórico. Merece hook próprio
   ou nota no AGENTS.md.
