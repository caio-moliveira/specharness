"""Anti-surveillance query guard (SPEC-013, ADR-008).

The metrics are for improving the spec+agent process, never for watching people.
Any query whose aggregation would single out an individual is refused here, at
the boundary, before it can touch a store — the pure predicate that decides is
`specharness_core.metrics.is_individual_query`.
"""

from __future__ import annotations

from collections.abc import Sequence

from specharness_core.metrics import INDIVIDUAL_AXES, is_individual_query


class SurveillanceRejected(Exception):
    """A query was refused because it would expose an individual (ADR-008)."""

    def __init__(self, dimensions: Sequence[str]) -> None:
        offending = sorted(d for d in dimensions if d.strip().lower() in INDIVIDUAL_AXES)
        super().__init__(
            "Consulta rejeitada pela política anti-vigilância (ADR-008): agregação "
            f"por indivíduo não é permitida ({', '.join(offending)}). A agregação "
            "mínima é spec/sprint/time."
        )


def guard_query(dimensions: Sequence[str]) -> None:
    """Raise `SurveillanceRejected` if any dimension would expose an individual."""
    if is_individual_query(dimensions):
        raise SurveillanceRejected(dimensions)
