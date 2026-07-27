"""The BDD verify gate's pure decisions (SPEC-012, ADR-016)."""

from __future__ import annotations

from specharness_core import (
    ScenarioRun,
    SpecStatus,
    VerifyReport,
    allows_done,
    done_edit_allowed,
    is_ci,
)


def _run(status, title="c"):
    return ScenarioRun("SPEC-042", title, status)


# --- VerifyReport veredito --------------------------------------------------


def test_all_green_only_when_every_scenario_passed():
    assert VerifyReport("SPEC-042", (_run("passed"), _run("passed"))).all_green is True
    assert VerifyReport("SPEC-042", (_run("passed"), _run("failed"))).all_green is False
    assert VerifyReport("SPEC-042", (_run("passed"), _run("pending"))).all_green is False


def test_no_scenarios_is_not_green():
    assert VerifyReport("SPEC-042", ()).all_green is False


def test_report_partitions_by_status():
    report = VerifyReport("SPEC-042", (_run("passed"), _run("failed"), _run("pending")))

    assert len(report.passed) == 1
    assert len(report.failed) == 1
    assert len(report.pending) == 1


# --- is_ci ------------------------------------------------------------------


def test_is_ci_reads_the_env():
    assert is_ci({"CI": "true"}) is True
    assert is_ci({"CI": "1"}) is True
    assert is_ci({"CI": "false"}) is False
    assert is_ci({}) is False


# --- allows_done (critério 3) -----------------------------------------------


def test_allows_done_needs_lifecycle_and_all_green():
    green = VerifyReport("SPEC-042", (_run("passed"),))
    red = VerifyReport("SPEC-042", (_run("failed"),))

    assert allows_done(SpecStatus.VERIFYING, green) is True
    assert allows_done(SpecStatus.VERIFYING, red) is False
    # a forma do lifecycle também tranca: ready -> done não é permitido
    assert allows_done(SpecStatus.READY, green) is False


# --- done_edit_allowed (critério 6, ADR-016) --------------------------------


def test_a_done_transition_outside_ci_is_rejected():
    assert done_edit_allowed(SpecStatus.DONE, SpecStatus.VERIFYING, in_ci=False) is False
    assert done_edit_allowed(SpecStatus.DONE, None, in_ci=False) is False


def test_a_done_transition_inside_ci_is_allowed():
    assert done_edit_allowed(SpecStatus.DONE, SpecStatus.VERIFYING, in_ci=True) is True


def test_an_already_done_spec_is_not_blocked():
    assert done_edit_allowed(SpecStatus.DONE, SpecStatus.DONE, in_ci=False) is True


def test_non_done_edits_are_always_allowed():
    assert done_edit_allowed(SpecStatus.VERIFYING, SpecStatus.IN_PROGRESS, in_ci=False) is True
