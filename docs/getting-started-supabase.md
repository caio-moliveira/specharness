# Getting started: specharness + Supabase

O specharness funciona com qualquer Postgres via `SPECHARNESS_DATABASE_URL`
(ADR-002); o Supabase é o caminho mais rápido para um Postgres gerenciado
gratuito. Este guia cobre a conexão e a **pegadinha do pooler** que custa uma
tarde de debugging se você não souber dela.

## 1. Pegue a connection string certa

No painel do Supabase: **Connect** (topo do projeto) → aba **Connection
String**. Você verá três opções — e a escolha importa:

| Opção | Host/porta | Serve para o specharness? |
|---|---|---|
| Direct connection | `db.<ref>.supabase.co:5432` | Sim, mas exige IPv6 (falha em muitas redes) |
| **Session pooler** | `aws-0-<região>.pooler.supabase.com:5432` | **Sim — recomendado** |
| Transaction pooler | `aws-0-<região>.pooler.supabase.com:6543` | Parcial — leia o aviso abaixo |

Use o **session pooler (porta 5432)**.

## 2. Configure o .env

```dotenv
SPECHARNESS_DATABASE_URL=postgresql+asyncpg://postgres.<ref>:<SENHA>@aws-0-<região>.pooler.supabase.com:5432/postgres
```

- O esquema é `postgresql+asyncpg://` — o specharness deriva sozinho a engine
  síncrona (psycopg, usada pelo CLI e pelas migrações) e a assíncrona
  (asyncpg, usada pelo server) da mesma URL (ADR-010).
- A senha vai na URL e a URL vai **só no `.env`** — nunca em
  `specharness.yaml` e nunca em commit. As mensagens de erro do specharness
  redigem a senha, mas a URL crua é sua responsabilidade.

## 3. Conecte e migre

```sh
uv run specharness connect db
```

Saída esperada: `✓ Conectado — PostgreSQL em ...` com a lista de migrações
aplicadas. O comando é idempotente: rodar de novo é no-op.

## ⚠️ A pegadinha do pooler (porta 6543)

O **transaction pooler** (porta `6543`, modo transação) não convive com os
*prepared statements* nomeados que o asyncpg, driver assíncrono do
specharness, usa por padrão. O sintoma é traiçoeiro — medimos na prática:

- `specharness connect db` **funciona** (as migrações usam a engine síncrona
  psycopg, que sobrevive ao modo transação);
- uma query assíncrona isolada **também funciona**;
- mas sob conexões concorrentes — o caso normal do server/dashboard — estoura
  `DuplicatePreparedStatementError: prepared statement "__asyncpg_stmt_1__"
  already exists` (ou o gêmeo `... does not exist`).

Ou seja: metade do produto conecta e a outra metade quebra, o que aponta o
diagnóstico para todo lugar menos a porta. **A correção é usar a porta 5432
(session pooler)** no host `...pooler.supabase.com`, que mantém a semântica de
sessão completa que o asyncpg espera.

Se você precisa do transaction pooler por outra razão (limite de conexões em
serverless), o workaround do asyncpg é desabilitar o cache de statements —
mas o caminho suportado pelo specharness é o session pooler.

## Erros comuns

| Sintoma | Causa | Correção |
|---|---|---|
| `não foi possível conectar` no connect db | Rede/host errado, ou direct connection sem IPv6 | Troque para o host `...pooler.supabase.com` |
| `autenticação` recusada | Senha errada ou usuário sem o sufixo do projeto | No pooler, o usuário é `postgres.<ref>`, não `postgres` |
| `prepared statement ... does not exist` no server | Porta 6543 (transaction pooler) | Use a porta 5432 (session pooler) |
| Migrações ok, dashboard vazio | Server apontando para outro banco (`.env` não carregado) | Confira `SPECHARNESS_DATABASE_URL` no ambiente do server |
