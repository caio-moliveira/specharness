---
name: entregar-spec
description: Fecha a entrega de uma spec implementada - roda os gates, monta o relatório de entrega com ponteiros para evidência, aciona o verificador independente e atualiza o status. Use quando o usuário pedir para finalizar, entregar ou fechar uma spec/US, ou ao concluir qualquer implementação de spec.
---

# entregar-spec

Princípio (ADR-016): seu relatório é **alegação com ponteiros para evidência**
— quem arbitra é o verificador independente e, por fim, o CI.

## Processo

1. Rode `just lint && just test` e `just test-integrity`. Vermelho = não há
   entrega; volte à implementação.
2. Monte a matriz cenário × teste (cada cenário Gherkin da spec → arquivo e
   função de teste). Cenário descoberto = não há entrega.
3. Meça cada success_metric verificável localmente (ex.: cobertura com
   `--cov`) e anote o comando usado. As dependentes de CI/produção ficam
   "pendente de CI".
4. Acione o subagente `verificar-spec` passando apenas o id da spec. Se
   REPROVADO: retorne à implementação com os bloqueadores; não prossiga.
5. Atualize a spec: `status: verifying` (NUNCA `done` — o hook rejeita;
   done é do CI), `updated:` com a data, desvios do especificado registrados
   no corpo da spec.
6. Commit final com trailer e o relatório abaixo na conversa.

## Template do relatório de entrega

```
## Entrega SPEC-NNN — <título>
Veredicto do verificador: APROVADO (contexto limpo)
Cenários: N/N cobertos — matriz cenário → teste
Success metrics: [métrica → valor medido → comando] | pendente de CI
Desvios da spec: nenhum | [o quê + por quê, registrado na spec]
Decisões: ADR-NNN | nenhuma
Follow-ups: ...
Commits: [hashes]
Evidência: [run local timestampado; CI assume no push]
```
