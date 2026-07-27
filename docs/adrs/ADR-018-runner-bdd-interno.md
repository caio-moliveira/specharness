# ADR-018 — Runner de BDD interno mínimo, não pytest-bdd, para o `verify`

- **Status:** aceita
- **Data:** 2026-07-27
- **Specs relacionadas:** SPEC-012 (emenda ADR-012)

## Contexto

O ADR-012 decidiu pytest-bdd como runner do gate BDD, mas nunca foi
implementado. A SPEC-012 (`specharness verify`) precisa localizar os cenários de
uma spec e executá-los, marcando cada um como passou/falhou/pendente. Desde o
ADR-012, o código evoluiu com implementações internas puras — `trailers.py`
espelha `git interpret-trailers`, `gherkin.py` parseia o subconjunto Gherkin sem
`gherkin-official`. Já temos, portanto, a estrutura dos cenários no core.

## Opções consideradas

1. **pytest-bdd (ADR-012)** — fiel ao registro; um só `just test`. Contras:
   depende de uma lib externa e de um layout de feature files, acopla a suíte do
   usuário a esse formato, e o parsing de resultado por cenário é frágil; a
   própria suíte do specharness não é pytest-bdd, então o `verify` não se
   dogfooda no repo.
2. **Runner interno mínimo** — um step registry (`padrão → callable`) sobre o
   `gherkin.py` já existente: step sem definição → pendente, step que levanta →
   falhou, todos passam → passou. Autocontido, sem dependência nova, testável
   hermeticamente, consistente com a filosofia do repo. Contra: reimplementa o
   casamento step↔definição (subconjunto do que pytest-bdd faz).

## Decisão

O `verify` usa um **runner interno mínimo de step registry** sobre o parser puro
de Gherkin, não pytest-bdd. A decisão do ADR-012 de usar BDD como gate de `done`
permanece; só o **mecanismo de execução** muda — daí este ADR substituir o
ADR-012. Escolhido por coerência com o padrão pure-internal já consolidado
(sem dependência externa, testável sem rede nem I/O de terceiros) e por permitir
que o `verify` rode contra qualquer suíte que registre step definitions.

## Consequências

Fica mais fácil: zero dependência nova; runner testável em contexto limpo;
"step ausente = pendente" é distinto de "falha" por construção. Fica mais
difícil: manter o matcher de steps à mão conforme a gramática crescer. Passa a
ser o padrão: step definitions do repositório são registradas via `@step` e o
`verify` as resolve — não há feature files pytest-bdd.
