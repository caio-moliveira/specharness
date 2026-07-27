"""Perception-sample persistence (SPEC-014, ADR-008)."""

from __future__ import annotations

from datetime import datetime

import pytest
from specharness_adapters.db import PerceptionStore, SqlAlchemyDatabaseGateway
from specharness_core import PerceptionSample
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target


@pytest.fixture
def target(tmp_path):
    resolved = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp_path)
    SqlAlchemyDatabaseGateway(resolved).migrate()
    return resolved


def _sample(pr: str, spec="SPEC-042", sprint="2026-A4", tempo="economizou") -> PerceptionSample:
    return PerceptionSample(
        pr_ref=pr,
        spec_id=spec,
        sprint=sprint,
        runtime="Claude Code",
        model="claude-opus",
        aproveitamento=5,
        retrabalho="leve",
        tempo_percebido=tempo,  # type: ignore[arg-type]
        comentario="fluiu",
    )


def test_a_recorded_sample_round_trips(target):
    store = PerceptionStore(target)
    store.record_sample(_sample("r#1"), datetime(2026, 7, 27))

    samples = store.samples_for_sprint("2026-A4")

    assert len(samples) == 1
    assert samples[0].pr_ref == "r#1"
    assert samples[0].tempo_percebido == "economizou"
    assert samples[0].comentario == "fluiu"


def test_has_response_is_true_after_a_sample(target):
    store = PerceptionStore(target)
    assert store.has_response("r#1") is False
    store.record_sample(_sample("r#1"), datetime(2026, 7, 27))
    assert store.has_response("r#1") is True


def test_a_skip_counts_as_a_response_but_not_a_sample(target):
    store = PerceptionStore(target)
    store.record_skip(
        "r#9", "SPEC-042", "2026-A4", "Claude Code", "claude-opus", datetime(2026, 7, 27)
    )

    assert store.has_response("r#9") is True  # no re-prompt for this PR
    assert store.samples_for_sprint("2026-A4") == []  # a skip is not a sample
    assert store.skips_for_sprint("2026-A4") == 1


def test_samples_are_scoped_by_sprint(target):
    store = PerceptionStore(target)
    store.record_sample(_sample("r#1", sprint="2026-A4"), datetime(2026, 7, 27))
    store.record_sample(_sample("r#2", sprint="2026-A5"), datetime(2026, 7, 27))

    assert [s.pr_ref for s in store.samples_for_sprint("2026-A4")] == ["r#1"]
    assert store.skips_for_sprint("2026-A9") == 0
