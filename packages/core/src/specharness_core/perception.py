"""Perception micro-survey — the pure domain (SPEC-014, ADR-008).

Camada 3 (SPEC-001 §8.4): the METR RCT showed perception alone misleads and
system-measured time alone doesn't explain — the value is in the *crossing*. So
this module keeps two things pure and deterministic:

- the survey answers as a validated `PerceptionSample` (three closed items plus an
  optional free comment), with a `skipped` record for a declined survey; and
- the sprint aggregate, whose headline is the *perception gap*: the fraction of
  samples whose perceived direction (economizou/neutro/custou) disagrees with the
  measured direction of the spec's cycle time relative to the sprint median.

Privacy is structural (ADR-008): a sample is anchored to PR/spec/runtime/model and
**never** to a respondent, and the aggregate exposes only counts and distributions
— there is deliberately no field through which an individual could be exposed.
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

Retrabalho = Literal["nenhum", "leve", "pesado"]
TempoPercebido = Literal["economizou", "neutro", "custou"]

_RETRABALHO: frozenset[str] = frozenset({"nenhum", "leve", "pesado"})
_TEMPO: frozenset[str] = frozenset({"economizou", "neutro", "custou"})

#: economizou = faster than expected (-1), custou = slower (+1), neutro = 0.
_TEMPO_DIRECTION: dict[str, int] = {"economizou": -1, "neutro": 0, "custou": 1}


class PerceptionError(ValueError):
    """A survey answer is outside its allowed domain (SPEC-014, acceptance)."""


@dataclass(frozen=True)
class PerceptionSample:
    """A single dev's answers for one merged PR, anchored to the triple.

    No respondent identity is stored — the anchor is (pr_ref, spec_id, runtime,
    model), never a person (ADR-008).
    """

    pr_ref: str
    spec_id: str
    sprint: str
    runtime: str
    model: str
    aproveitamento: int  # 1..5
    retrabalho: Retrabalho
    tempo_percebido: TempoPercebido
    comentario: str | None = None


@dataclass(frozen=True)
class SprintPerception:
    """Aggregated perception for a sprint — only counts and distributions."""

    sprint: str
    n_samples: int
    n_skipped: int
    aproveitamento_mean: float | None
    retrabalho_dist: Mapping[str, int]
    tempo_dist: Mapping[str, int]
    perception_gap: float | None


def validate_answers(aproveitamento: int, retrabalho: str, tempo_percebido: str) -> None:
    """Raise `PerceptionError` if any closed item is outside its domain."""
    if not 1 <= aproveitamento <= 5:
        raise PerceptionError("aproveitamento deve estar entre 1 e 5")
    if retrabalho not in _RETRABALHO:
        raise PerceptionError("retrabalho deve ser nenhum, leve ou pesado")
    if tempo_percebido not in _TEMPO:
        raise PerceptionError("tempo percebido deve ser economizou, neutro ou custou")


def perceived_direction(tempo_percebido: str) -> int:
    """Map the perceived-time category to a direction: -1 faster, 0, +1 slower."""
    return _TEMPO_DIRECTION[tempo_percebido]


def measured_direction(cycle_time: float, median: float) -> int:
    """Direction of a spec's cycle time relative to the sprint median.

    Below the median is faster than typical (-1), above is slower (+1), exactly at
    the median is neutral (0) — the same axis the perceived direction lives on.
    """
    if cycle_time < median:
        return -1
    if cycle_time > median:
        return 1
    return 0


def perception_gap(
    samples: Sequence[PerceptionSample], cycle_times: Mapping[str, float]
) -> float | None:
    """Fraction of samples whose perceived direction disagrees with the measured one.

    Only samples whose spec has a known cycle time are comparable; the median is
    taken over those cycle times. Returns None when nothing is comparable.
    """
    comparable = [s for s in samples if s.spec_id in cycle_times]
    if not comparable:
        return None
    median = statistics.median(cycle_times[s.spec_id] for s in comparable)
    divergent = sum(
        1
        for s in comparable
        if perceived_direction(s.tempo_percebido)
        != measured_direction(cycle_times[s.spec_id], median)
    )
    return divergent / len(comparable)


def aggregate_perception(
    sprint: str,
    samples: Sequence[PerceptionSample],
    n_skipped: int,
    cycle_times: Mapping[str, float],
) -> SprintPerception:
    """Aggregate a sprint's samples — counts, distributions and the perception gap.

    Never returns per-respondent data (ADR-008): the output is exactly the shape
    the dashboard may show.
    """
    retrabalho_dist = {key: 0 for key in ("nenhum", "leve", "pesado")}
    tempo_dist = {key: 0 for key in ("economizou", "neutro", "custou")}
    for sample in samples:
        retrabalho_dist[sample.retrabalho] += 1
        tempo_dist[sample.tempo_percebido] += 1
    mean = statistics.mean(s.aproveitamento for s in samples) if samples else None
    return SprintPerception(
        sprint=sprint,
        n_samples=len(samples),
        n_skipped=n_skipped,
        aproveitamento_mean=mean,
        retrabalho_dist=retrabalho_dist,
        tempo_dist=tempo_dist,
        perception_gap=perception_gap(samples, cycle_times),
    )
