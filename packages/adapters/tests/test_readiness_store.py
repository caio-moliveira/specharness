"""Cache and override persistence for the LLM gate (SPEC-011, critérios 3 e 5)."""

from __future__ import annotations

from datetime import date, datetime

import pytest
from specharness_adapters.db import OverrideStore, ReadinessCacheStore, SqlAlchemyDatabaseGateway
from specharness_core.assessment import Evaluation, Override, ReadinessIssue
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target


@pytest.fixture
def target(tmp_path):
    resolved = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(resolved).migrate()
    return resolved


def _evaluation(score=85):
    return Evaluation(
        score=score,
        issues=(ReadinessIssue(category="ambiguidade", description="d", suggestion="s"),),
        model="ollama/qwen3:8b",
        cost_usd=0.0012,
        cached=False,
    )


# --- cache (critério 5, métrica 3) -----------------------------------------


def test_a_cache_miss_returns_none(target):
    assert ReadinessCacheStore(target).get("nao-existe") is None


def test_put_then_get_roundtrips_and_marks_cached(target):
    store = ReadinessCacheStore(target)
    store.put("abc", _evaluation(85), datetime(2026, 7, 27))

    got = store.get("abc")

    assert got is not None
    assert got.score == 85
    assert got.cached is True
    assert got.model == "ollama/qwen3:8b"
    assert got.issues[0].category == "ambiguidade"
    assert got.cost_usd == 0.0012


def test_put_is_idempotent_by_hash(target):
    store = ReadinessCacheStore(target)
    store.put("abc", _evaluation(85), datetime(2026, 7, 27))
    store.put("abc", _evaluation(90), datetime(2026, 7, 28))

    assert store.get("abc").score == 90  # merge sobrescreve, não duplica


# --- override audit (critério 3) -------------------------------------------


def test_overrides_are_recorded_append_only_and_listed(target):
    store = OverrideStore(target)
    store.record(Override("SPEC-042", "Ana", "urgência", date(2026, 7, 27)))
    store.record(Override("SPEC-042", "Bob", "release", date(2026, 7, 28)))

    overrides = store.all_for("SPEC-042")

    assert [o.author for o in overrides] == ["Ana", "Bob"]
    assert overrides[0].justification == "urgência"
    assert store.all_for("SPEC-999") == []
