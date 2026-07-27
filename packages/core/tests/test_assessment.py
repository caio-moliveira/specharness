"""The LLM Readiness Gate domain (SPEC-011)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError
from specharness_core import Evaluation, Override, ReadinessAssessment, ReadinessIssue, content_hash


def _issue(category="ambiguidade"):
    return ReadinessIssue(category=category, description="d", suggestion="s")


# --- schema (métrica 2: saída validada) ------------------------------------


def test_score_out_of_range_is_rejected():
    ReadinessAssessment(score=0)
    ReadinessAssessment(score=100)
    with pytest.raises(ValidationError):
        ReadinessAssessment(score=101)
    with pytest.raises(ValidationError):
        ReadinessAssessment(score=-1)


def test_issue_category_is_constrained_to_the_taxonomy():
    _issue("testabilidade")
    with pytest.raises(ValidationError):
        ReadinessIssue(category="inexistente", description="d", suggestion="s")


# --- Evaluation.blocks (critério 2) ----------------------------------------


def test_evaluation_blocks_only_below_threshold():
    assert Evaluation(69, (), "m", None).blocks(70) is True
    assert Evaluation(70, (), "m", None).blocks(70) is False
    assert Evaluation(90, (), "m", None).blocks(70) is False


def test_cost_label():
    assert Evaluation(80, (), "m", None).cost_label == "n/d"
    assert Evaluation(80, (), "m", 0.0012).cost_label.startswith("US$")


# --- content_hash (critério 5, métrica 3) ----------------------------------


def test_content_hash_is_stable_and_content_sensitive():
    assert content_hash("texto") == content_hash("texto")
    assert content_hash("texto") != content_hash("outro")


def test_the_salt_changes_the_hash_so_a_prompt_change_reevaluates():
    assert content_hash("texto", "1") != content_hash("texto", "2")
    assert content_hash("texto", "1") != content_hash("texto")


# --- Override (critério 3) --------------------------------------------------


def test_override_carries_the_audit_fields():
    override = Override(
        spec_id="SPEC-042", author="Ana", justification="urgência de release", at=date(2026, 7, 27)
    )

    assert override.author == "Ana"
    assert override.justification == "urgência de release"
    assert override.at == date(2026, 7, 27)
