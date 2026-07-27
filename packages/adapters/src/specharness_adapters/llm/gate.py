"""The LLM Readiness Gate call (SPEC-011, ADR-006).

The prompt lives here (like `_PING_PROMPT`), next to the litellm call. The schema
and the score→block decision are pure core (`assessment.py`). Métrica 2: the
model's output MUST validate against `ReadinessAssessment`; a validation failure
is retried automatically, never parsed as free text.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import ValidationError
from specharness_core.assessment import Evaluation, ReadinessAssessment
from specharness_core.ports.llm import LLMError, LLMTarget

#: Bump when the prompt changes, so the cache re-evaluates (SPEC-011, critério 5)
#: and the golden dataset must go green again in CI (critério 4).
PROMPT_VERSION = "1"

DEFAULT_MAX_RETRIES = 2

_GATE_PROMPT = """Você é um revisor sênior avaliando a prontidão de uma spec para \
desenvolvimento (Definition of Ready). Julgue apenas o que é semântico: \
testabilidade (cada critério é verificável?), ambiguidade (duas pessoas \
implementariam a mesma coisa?), contradição (conflita com si mesma?) e \
completude (os cenários cobrem erros, vazios e casos-limite?).

Responda um JSON com:
- `score`: inteiro 0-100 (abaixo de 70 = não pronta; 70-89 = pronta com \
ressalvas; 90+ = pronta).
- `issues`: lista de problemas, cada um com `category` (um de: testabilidade, \
ambiguidade, contradição, completude), `description` e `suggestion` (como \
corrigir). Liste apenas problemas reais; uma spec ótima pode ter `issues` vazio.

A spec a avaliar:

{spec}
"""


class SupportsStructuredWithCost(Protocol):
    """The slice of the LLM client the gate needs."""

    @property
    def target(self) -> LLMTarget: ...

    def structured_with_cost(
        self, prompt: str, schema: type[ReadinessAssessment]
    ) -> tuple[ReadinessAssessment, float | None]: ...


def build_prompt(spec_text: str) -> str:
    return _GATE_PROMPT.format(spec=spec_text)


def evaluate_spec(
    spec_text: str,
    client: SupportsStructuredWithCost,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
) -> Evaluation:
    """Evaluate a spec via the LLM, retrying on a schema-validation failure."""
    prompt = build_prompt(spec_text)
    last_error: ValidationError | None = None
    for _ in range(max_retries + 1):
        try:
            assessment, cost = client.structured_with_cost(prompt, ReadinessAssessment)
        except ValidationError as exc:
            last_error = exc
            continue
        return Evaluation(
            score=assessment.score,
            issues=tuple(assessment.issues),
            model=client.target.model,
            cost_usd=cost,
            cached=False,
        )
    raise LLMError.for_provider(
        client.target.provider,
        f"o modelo não retornou uma avaliação válida após {max_retries + 1} tentativas",
    ) from last_error
