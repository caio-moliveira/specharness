"""Pure perception domain (SPEC-014). Deterministic over the samples given."""

from __future__ import annotations

import pytest
from specharness_core import (
    PerceptionError,
    PerceptionSample,
    aggregate_perception,
    measured_direction,
    perceived_direction,
    perception_gap,
    validate_answers,
)


def _sample(spec_id: str, tempo: str, aproveitamento: int = 4) -> PerceptionSample:
    return PerceptionSample(
        pr_ref=f"caio/repo#{spec_id[-3:]}",
        spec_id=spec_id,
        sprint="2026-A4",
        runtime="Claude Code",
        model="claude-opus",
        aproveitamento=aproveitamento,
        retrabalho="leve",
        tempo_percebido=tempo,  # type: ignore[arg-type]
    )


# --- validation -------------------------------------------------------------


def test_valid_answers_pass():
    validate_answers(3, "leve", "neutro")  # no raise


@pytest.mark.parametrize("value", [0, 6, -1])
def test_aproveitamento_out_of_range_is_rejected(value):
    with pytest.raises(PerceptionError):
        validate_answers(value, "leve", "neutro")


def test_unknown_retrabalho_is_rejected():
    with pytest.raises(PerceptionError):
        validate_answers(3, "medio", "neutro")


def test_unknown_tempo_is_rejected():
    with pytest.raises(PerceptionError):
        validate_answers(3, "leve", "rápido")


# --- directions -------------------------------------------------------------


def test_perceived_direction_maps_the_category():
    assert perceived_direction("economizou") == -1
    assert perceived_direction("neutro") == 0
    assert perceived_direction("custou") == 1


def test_measured_direction_relative_to_median():
    assert measured_direction(50.0, 100.0) == -1  # faster than typical
    assert measured_direction(150.0, 100.0) == 1  # slower
    assert measured_direction(100.0, 100.0) == 0


# --- perception gap ---------------------------------------------------------


def test_gap_is_none_without_comparable_samples():
    # sample's spec has no known cycle time
    assert perception_gap([_sample("SPEC-001", "custou")], {}) is None


def test_gap_counts_divergent_directions():
    samples = [
        _sample("SPEC-A", "economizou"),  # perceived -1; cycle 50 < median -> -1 agree
        _sample("SPEC-B", "economizou"),  # perceived -1; cycle 150 > median -> +1 DIVERGE
    ]
    cycle_times = {"SPEC-A": 50.0, "SPEC-B": 150.0}
    # median of [50, 150] = 100 -> A agrees, B diverges -> 1/2
    assert perception_gap(samples, cycle_times) == 0.5


def test_gap_is_zero_when_all_agree():
    samples = [_sample("SPEC-A", "economizou"), _sample("SPEC-B", "custou")]
    cycle_times = {"SPEC-A": 50.0, "SPEC-B": 150.0}
    assert perception_gap(samples, cycle_times) == 0.0


def test_gap_ignores_samples_without_a_cycle_time():
    samples = [_sample("SPEC-A", "economizou"), _sample("SPEC-Z", "custou")]
    # only SPEC-A is comparable; median over [50] = 50; A: 50 not < 50 -> measured 0,
    # perceived -1 -> diverge -> 1/1
    assert perception_gap(samples, {"SPEC-A": 50.0}) == 1.0


# --- aggregation ------------------------------------------------------------


def test_aggregate_reports_only_counts_and_distributions():
    samples = [
        _sample("SPEC-A", "economizou", aproveitamento=5),
        _sample("SPEC-B", "custou", aproveitamento=3),
    ]
    agg = aggregate_perception("2026-A4", samples, n_skipped=2, cycle_times={})

    assert agg.sprint == "2026-A4"
    assert agg.n_samples == 2
    assert agg.n_skipped == 2
    assert agg.aproveitamento_mean == 4.0
    assert agg.tempo_dist == {"economizou": 1, "neutro": 0, "custou": 1}
    assert agg.retrabalho_dist == {"nenhum": 0, "leve": 2, "pesado": 0}
    assert agg.perception_gap is None  # no cycle times
    # the aggregate has no field carrying a respondent identity
    assert not any("resp" in f or "author" in f or "dev" in f for f in vars(agg))


def test_aggregate_of_an_empty_sprint_has_no_mean():
    agg = aggregate_perception("2026-A4", [], n_skipped=0, cycle_times={})
    assert agg.n_samples == 0
    assert agg.aproveitamento_mean is None
