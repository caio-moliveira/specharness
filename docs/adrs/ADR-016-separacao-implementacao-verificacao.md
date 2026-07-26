# ADR-016 — Quem implementa não arbitra: separação estrutural entre implementação e verificação

- **Status:** aceita
- **Data:** 2026-07-26
- **Specs relacionadas:** SPEC-002, SPEC-012, SPEC-013

## Contexto

Agentes de código avaliando o próprio trabalho exibem self-grading bias e
reward hacking documentados: afrouxam asserts, adicionam skips, mockam a
realidade até o teste passar e reportam métricas que ninguém confere. O RCT
da METR (2025) mostrou 39 pontos de gap entre velocidade percebida e real —
auto-relato mente mesmo de boa fé. Se as métricas do specharness puderem ser
geradas pelo mesmo agente que escreveu o código, a tese central do produto
("specs prontas produzem código que sobrevive") fica indefensável diante de
qualquer cético.

## Opções consideradas

1. **Confiar no auto-relato do agente com revisão humana amostral** — barato,
   mas o viés é sistemático e a amostragem não o corrige; a credibilidade das
   métricas morre no primeiro caso de gaming descoberto.
2. **Revisor humano obrigatório em toda entrega** — não escala e devolve ao
   humano exatamente o trabalho que o produto promete tirar dele.
3. **Separação estrutural** — o CI é o único árbitro de transições e
   métricas; auto-relato vira alegação com ponteiros para evidência;
   verificação roda em contexto limpo, separado da implementação.

## Decisão

Quem implementa não arbitra. Em ambos os níveis (nosso desenvolvimento e o
produto): (a) a transição `verifying → done` é executada exclusivamente pelo
pipeline de CI com BDD verde — edição local de status para `done` é rejeitada
pelo hook de schema; (b) métricas são calculadas exclusivamente de artefatos
brutos (git, CI, tracker) — números auto-relatados por agentes nunca entram no
banco de métricas; (c) `first-run` é o primeiro run no CI após `ready`, nunca
execução local; (d) testes são protegidos do implementador: edição de
`tests/` em tarefa de implementação exige confirmação, e o CI roda checagem de
integridade (asserts removidos, skips sem justificativa) + gate de cobertura;
(e) a verificação de entrega roda em subagente com contexto limpo — recebe
apenas a spec e o diff, sem o histórico da sessão de implementação.

## Consequências

Métricas defensáveis publicamente; o relatório de entrega do agente vira
narrativa auditável com ponteiros, não fonte de dados. Sinais de
test-tampering viram feature do produto (relatório de higiene, SPEC-013).
Custo: fricção deliberada ao editar testes durante implementação e dependência
do CI para fechar specs — ambos aceitos conscientemente.
