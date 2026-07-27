"""Anti-surveillance query guard (SPEC-013, ADR-008)."""

from __future__ import annotations

import pytest
from specharness_adapters.metrics import SurveillanceRejected, guard_query


def test_aggregate_dimensions_pass():
    guard_query(["spec", "sprint", "team"])  # no raise


def test_a_query_by_author_is_rejected():
    with pytest.raises(SurveillanceRejected) as excinfo:
        guard_query(["sprint", "author"])
    message = str(excinfo.value)
    assert "ADR-008" in message
    assert "author" in message


def test_rejection_names_every_offending_axis():
    with pytest.raises(SurveillanceRejected) as excinfo:
        guard_query(["committer", "assignee"])
    message = str(excinfo.value)
    assert "assignee" in message and "committer" in message
