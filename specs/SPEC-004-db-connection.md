---
spec: SPEC-004
title: "Onboarding: conexão de banco (SQLite default, Postgres opcional)"
status: ready
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
