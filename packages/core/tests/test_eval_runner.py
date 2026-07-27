"""The golden-dataset eval runner (SPEC-011, critério 4, métrica 1)."""

from __future__ import annotations

from evals.runner.__main__ import run
from evals.runner.gate_eval import (
    in_range_rate,
    meets_criteria,
    parse_golden,
    reachable_models,
    score_in_range,
)


def test_parse_golden_extracts_range_and_embedded_spec():
    text = "---\nexpected_range: [0, 55]\n---\n```markdown\nconteúdo da spec ruim\n```\n"

    golden = parse_golden("bad.md", text)

    assert golden.expected_range == (0, 55)
    assert "conteúdo da spec ruim" in golden.spec_text


def test_parse_golden_keeps_a_nested_gherkin_fence_whole():
    text = (
        "---\nexpected_range: [85, 100]\n---\n"
        "```markdown\nspec\n\n```gherkin\n# language: pt\nCenário: c\n```\n```\n"
    )

    golden = parse_golden("good.md", text)

    assert "Cenário: c" in golden.spec_text  # o fence aninhado não truncou


def test_score_in_range():
    assert score_in_range(50, (0, 55)) is True
    assert score_in_range(60, (0, 55)) is False
    assert score_in_range(85, (85, 100)) is True


def test_rate_and_criteria():
    assert in_range_rate([True, True, False, True]) == 0.75
    assert in_range_rate([]) == 0.0
    assert meets_criteria(0.9, {"score_in_range_rate": 0.9}) is True
    assert meets_criteria(0.89, {"score_in_range_rate": 0.9}) is False


def test_reachable_models_filters_by_key_and_ollama():
    models = ["anthropic/claude", "ollama/qwen3:8b"]

    assert reachable_models(models, {"ANTHROPIC_API_KEY": "k"}, ollama_up=False) == [
        "anthropic/claude"
    ]
    assert reachable_models(models, {}, ollama_up=True) == ["ollama/qwen3:8b"]
    assert reachable_models(models, {}, ollama_up=False) == []


# --- run() sobre o dataset real do repo, com evaluator injetado ------------


def test_run_skips_honestly_when_no_model_is_reachable():
    code = run(env={}, evaluator=lambda model, spec: 0, ollama_up=False)

    assert code == 0  # estrutura ok, execução real pulada — CI verde por honestidade


def test_run_passes_when_scores_land_in_range():
    def evaluator(model, spec):
        return 40 if "Busca" in spec else 92  # bad-spec fala de "Busca"; good não

    code = run(env={"ANTHROPIC_API_KEY": "k"}, evaluator=evaluator, ollama_up=False)

    assert code == 0


def test_run_fails_when_scores_fall_out_of_range():
    code = run(env={"ANTHROPIC_API_KEY": "k"}, evaluator=lambda model, spec: 50, ollama_up=False)

    assert code == 1  # 50 está fora de [85,100] do golden bom → abaixo de 90%
