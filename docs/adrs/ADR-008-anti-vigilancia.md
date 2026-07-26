# ADR-008 — Métricas medem processo/spec/agente — nunca o indivíduo

- **Status:** aceita
- **Data:** 2026-07-25
- **Specs relacionadas:** SPEC-001, SPEC-002

## Contexto

Ferramentas de métricas que viram vigilância individual morrem na adoção e corrompem os próprios dados (Lei de Goodhart). O valor do specharness está em medir o processo e os agentes, não em ranquear pessoas.

## Opções consideradas

1. Permitir corte por indivíduo 'para quem quiser' — a exceção viraria o uso principal
2. Proibir estruturalmente: agregação mínima spec/sprint/time, consultas por autor rejeitadas pela API

## Decisão

Nenhuma métrica é exposta por indivíduo. A restrição é estrutural (API rejeita), não configurável. Este princípio está acima de feature request.

## Consequências

Confiança do time como pré-condição de dados honestos; recusa consciente de um segmento de mercado (gestão por vigilância).
