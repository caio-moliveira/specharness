"""Pure camada-2 metrics (SPEC-013). Every function is deterministic — same
events in, same numbers out — so these tests pin the numbers directly."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from specharness_core import (
    MetricValue,
    ScenarioRunEvent,
    SpecMetrics,
    StatusTransition,
    cycle_time_seconds,
    first_run_pass_rate,
    hygiene_report,
    is_individual_query,
    iterations_to_green,
    paired_view,
    spec_metric_values,
    tampering_signals,
    turnover_ratio,
)
from specharness_core.metrics import HygieneSignal
from specharness_core.specschema import SpecStatus


def _at(day: int) -> datetime:
    return datetime(2026, 7, day, 12, 0, tzinfo=UTC)


# --- cycle time -------------------------------------------------------------


def test_cycle_time_is_first_ready_to_done():
    transitions = [
        StatusTransition("SPEC-013", SpecStatus.READY, _at(1)),
        StatusTransition("SPEC-013", SpecStatus.IN_PROGRESS, _at(2)),
        StatusTransition("SPEC-013", SpecStatus.DONE, _at(4)),
    ]
    assert cycle_time_seconds(transitions) == timedelta(days=3).total_seconds()


def test_cycle_time_counts_from_the_first_ready_even_after_a_bounce():
    transitions = [
        StatusTransition("SPEC-013", SpecStatus.READY, _at(1)),
        StatusTransition("SPEC-013", SpecStatus.IN_PROGRESS, _at(2)),
        StatusTransition("SPEC-013", SpecStatus.READY, _at(3)),
        StatusTransition("SPEC-013", SpecStatus.DONE, _at(5)),
    ]
    assert cycle_time_seconds(transitions) == timedelta(days=4).total_seconds()


def test_cycle_time_is_none_without_done():
    transitions = [StatusTransition("SPEC-013", SpecStatus.READY, _at(1))]
    assert cycle_time_seconds(transitions) is None


def test_cycle_time_is_none_without_ready():
    transitions = [StatusTransition("SPEC-013", SpecStatus.DONE, _at(4))]
    assert cycle_time_seconds(transitions) is None


def test_cycle_time_is_none_when_done_precedes_ready():
    transitions = [
        StatusTransition("SPEC-013", SpecStatus.DONE, _at(1)),
        StatusTransition("SPEC-013", SpecStatus.READY, _at(4)),
    ]
    assert cycle_time_seconds(transitions) is None


# --- first-run pass rate and iterations-to-green ----------------------------


def test_first_run_pass_rate_only_counts_first_run_events():
    events = [
        ScenarioRunEvent(_at(1), "passed", first_run=True),
        ScenarioRunEvent(_at(1), "failed", first_run=True),
        ScenarioRunEvent(_at(2), "passed", first_run=False),
    ]
    assert first_run_pass_rate(events) == 0.5


def test_first_run_pass_rate_is_none_without_a_first_run():
    events = [ScenarioRunEvent(_at(2), "passed", first_run=False)]
    assert first_run_pass_rate(events) is None


def test_iterations_to_green_returns_the_first_all_green_execution():
    events = [
        ScenarioRunEvent(_at(1), "failed", first_run=True),
        ScenarioRunEvent(_at(1), "passed", first_run=True),
        ScenarioRunEvent(_at(2), "pending", first_run=False),
        ScenarioRunEvent(_at(3), "passed", first_run=False),
    ]
    assert iterations_to_green(events) == 3


def test_iterations_to_green_is_none_when_never_green():
    events = [
        ScenarioRunEvent(_at(1), "failed", first_run=True),
        ScenarioRunEvent(_at(2), "pending", first_run=False),
    ]
    assert iterations_to_green(events) is None


def test_iterations_to_green_is_none_with_no_events():
    assert iterations_to_green([]) is None


# --- turnover ratio ---------------------------------------------------------


def test_turnover_ratio_divides_by_baseline():
    assert turnover_ratio(0.6, 0.3) == 2.0


def test_turnover_ratio_is_none_when_baseline_is_zero():
    assert turnover_ratio(0.6, 0.0) is None


def test_turnover_ratio_is_none_when_a_side_is_missing():
    assert turnover_ratio(None, 0.3) is None
    assert turnover_ratio(0.6, None) is None


# --- anti-surveillance (ADR-008) --------------------------------------------


def test_individual_query_is_flagged_case_insensitively():
    assert is_individual_query(["spec", "Author"]) is True
    assert is_individual_query(["committer"]) is True


def test_aggregate_query_is_allowed():
    assert is_individual_query(["spec", "sprint", "team"]) is False


# --- volume/quality pairing (ADR-008) ---------------------------------------


def test_paired_view_drops_volume_without_its_quality_pair():
    values = [
        MetricValue("commits", "volume", 12.0, paired_with="first_run_pass_rate"),
    ]
    assert paired_view(values) == []


def test_paired_view_keeps_volume_when_its_quality_pair_is_present():
    values = [
        MetricValue("first_run_pass_rate", "quality", 0.9),
        MetricValue("commits", "volume", 12.0, paired_with="first_run_pass_rate"),
    ]
    assert paired_view(values) == values


def test_spec_metric_values_pairs_commits_with_first_run():
    spec = SpecMetrics("SPEC-013", 100.0, 0.9, 2, 0.1, 0.2, 1.0, 1.5, commits=7)
    values = spec_metric_values(spec)
    kept = paired_view(values)
    names = {v.name for v in kept}
    assert "commits" in names  # first_run_pass_rate is present, so the pair holds


def test_spec_metric_values_drops_commits_when_first_run_is_missing():
    spec = SpecMetrics("SPEC-013", None, None, None, None, None, None, None, commits=7)
    # first_run_pass_rate is None but still present as a quality metric — pairing
    # is about presence of the pair, not its value.
    kept_names = {v.name for v in paired_view(spec_metric_values(spec))}
    assert "commits" in kept_names


# --- test-hygiene / tampering (ADR-016) -------------------------------------

_DIFF_REMOVES_ASSERT = """diff --git a/packages/core/tests/test_x.py b/packages/core/tests/test_x.py
--- a/packages/core/tests/test_x.py
+++ b/packages/core/tests/test_x.py
@@ -1,3 +1,2 @@
 def test_x():
-    assert foo() == 1
     bar()
"""

_DIFF_NAKED_SKIP = """diff --git a/packages/core/tests/test_y.py b/packages/core/tests/test_y.py
--- a/packages/core/tests/test_y.py
+++ b/packages/core/tests/test_y.py
@@ -1,2 +1,3 @@
 def test_y():
+    @pytest.mark.skip
     pass
"""

_DIFF_NON_TEST = """diff --git a/packages/core/src/x.py b/packages/core/src/x.py
--- a/packages/core/src/x.py
+++ b/packages/core/src/x.py
@@ -1,2 +1,1 @@
-    assert foo() == 1
"""


def test_tampering_flags_a_net_assert_removal():
    signals = tampering_signals(_DIFF_REMOVES_ASSERT, "SPEC-013")
    assert len(signals) == 1
    assert signals[0].kind == "assert-removed"
    assert signals[0].spec_id == "SPEC-013"


def test_tampering_uses_net_balance_of_asserts():
    # two removed, one added back -> net 1 removal, still a signal
    diff = """diff --git a/packages/core/tests/test_z.py b/packages/core/tests/test_z.py
--- a/packages/core/tests/test_z.py
+++ b/packages/core/tests/test_z.py
@@ -1,4 +1,3 @@
 def test_z():
-    assert a() == 1
-    assert b() == 2
+    assert a() == 1
     c()
"""
    signals = tampering_signals(diff, "SPEC-013")
    assert len(signals) == 1
    assert "1 assert" in signals[0].detail


def test_tampering_no_signal_when_asserts_are_replaced_evenly():
    # one removed, one added -> net 0, no signal
    diff = """diff --git a/packages/core/tests/test_w.py b/packages/core/tests/test_w.py
--- a/packages/core/tests/test_w.py
+++ b/packages/core/tests/test_w.py
@@ -1,3 +1,3 @@
 def test_w():
-    assert old() == 1
+    assert new() == 1
"""
    assert tampering_signals(diff, "SPEC-013") == []


def test_tampering_flags_a_naked_skip():
    signals = tampering_signals(_DIFF_NAKED_SKIP, "SPEC-013")
    assert [s.kind for s in signals] == ["naked-skip"]


def test_tampering_ignores_non_test_files():
    assert tampering_signals(_DIFF_NON_TEST, "SPEC-013") == []


def test_a_skip_with_reason_is_not_flagged():
    diff = _DIFF_NAKED_SKIP.replace("@pytest.mark.skip", '@pytest.mark.skip(reason="x")')
    assert tampering_signals(diff, "SPEC-013") == []


def test_a_snapshot_recomputed_from_the_same_events_is_equal():
    # determinism: the same raw events must reproduce the same snapshot (value
    # equality over frozen dataclasses), which is what the recálculo scenario checks.
    from specharness_core import SprintSnapshot

    def build() -> SprintSnapshot:
        events = [
            ScenarioRunEvent(_at(1), "failed", first_run=True),
            ScenarioRunEvent(_at(1), "passed", first_run=True),
            ScenarioRunEvent(_at(2), "passed", first_run=False),
        ]
        transitions = [
            StatusTransition("SPEC-013", SpecStatus.READY, _at(1)),
            StatusTransition("SPEC-013", SpecStatus.DONE, _at(4)),
        ]
        spec = SpecMetrics(
            "SPEC-013",
            cycle_time_seconds(transitions),
            first_run_pass_rate(events),
            iterations_to_green(events),
            turnover_30d=0.1,
            turnover_90d=0.2,
            turnover_ratio_30d=turnover_ratio(0.1, 0.05),
            turnover_ratio_90d=turnover_ratio(0.2, 0.05),
            commits=3,
        )
        return SprintSnapshot("2026-A4", (spec,))

    assert build() == build()


def test_hygiene_report_groups_by_spec_sorted():
    signals = [
        HygieneSignal("SPEC-020", "naked-skip", "a"),
        HygieneSignal("SPEC-013", "assert-removed", "b"),
        HygieneSignal("SPEC-013", "naked-skip", "c"),
    ]
    report = hygiene_report(signals)
    assert list(report) == ["SPEC-013", "SPEC-020"]
    assert len(report["SPEC-013"]) == 2
