"""The LLM Readiness Gate call (SPEC-011, métrica 2: schema + retry)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from specharness_adapters.llm import build_prompt, evaluate_spec
from specharness_core.assessment import ReadinessAssessment, ReadinessIssue
from specharness_core.ports.llm import LLMError


def _assessment(score=85):
    return ReadinessAssessment(
        score=score,
        issues=[ReadinessIssue(category="ambiguidade", description="d", suggestion="s")],
    )


def _validation_error() -> ValidationError:
    try:
        ReadinessAssessment(score=999)  # fora de 0-100
    except ValidationError as exc:
        return exc
    raise AssertionError("esperava ValidationError")


class FakeClient:
    """Yields canned (assessment | exception, cost) pairs per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.target = SimpleNamespace(model="ollama/qwen3:8b", provider="ollama")
        self.calls = 0

    def structured_with_cost(self, prompt, schema):
        self.calls += 1
        item, cost = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item, cost


def test_evaluate_returns_score_issues_model_and_cost():
    client = FakeClient([(_assessment(85), 0.0012)])

    evaluation = evaluate_spec("uma spec", client)

    assert evaluation.score == 85
    assert evaluation.issues[0].category == "ambiguidade"
    assert evaluation.cost_usd == 0.0012
    assert evaluation.model == "ollama/qwen3:8b"
    assert evaluation.cached is False
    assert client.calls == 1


def test_a_schema_failure_is_retried_then_succeeds():
    client = FakeClient([(_validation_error(), None), (_assessment(70), 0.0)])

    evaluation = evaluate_spec("s", client, max_retries=2)

    assert evaluation.score == 70
    assert client.calls == 2  # falhou uma vez, tentou de novo


def test_exhausted_retries_raise_an_llm_error_not_a_validation_error():
    client = FakeClient([(_validation_error(), None)] * 3)

    with pytest.raises(LLMError):
        evaluate_spec("s", client, max_retries=2)

    assert client.calls == 3  # tentativa inicial + 2 retries


def test_the_prompt_includes_the_spec_text():
    assert "MINHA SPEC AQUI" in build_prompt("MINHA SPEC AQUI")


def test_structured_with_cost_validates_and_prices_on_the_real_client():
    from specharness_adapters.llm.client import LiteLlmClient
    from specharness_core.ports.llm import LLMTarget

    content = ReadinessAssessment(score=88, issues=[]).model_dump_json()

    def fake_completion(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
            _hidden_params={"response_cost": 0.002},
        )

    client = LiteLlmClient(
        LLMTarget("ollama", "ollama/qwen3:8b", "http://x", None), {}, completion_fn=fake_completion
    )

    assessment, cost = client.structured_with_cost("p", ReadinessAssessment)

    assert assessment.score == 88
    assert cost == 0.002
