"""LLM narrative with the read-before-cite regeneration loop (SPEC-015)."""

from __future__ import annotations

from specharness_adapters.report import generate_narrative
from specharness_core.linking import LinkingResult
from specharness_core.metrics import SpecMetrics, SprintSnapshot
from specharness_core.perception import SprintPerception
from specharness_core.report import build_report


def _report():
    snapshot = SprintSnapshot(
        "2026-A4", (SpecMetrics("SPEC-013", 360000.0, 0.9, 2, 0.1, 0.2, 1.0, 1.5, 8),)
    )
    perception = SprintPerception("2026-A4", 3, 1, 4.0, {}, {}, 0.25)
    return build_report(
        "2026-A4", snapshot, perception, LinkingResult((), (), ()), {"SPEC-013": "done"}
    )


def test_a_faithful_narrative_is_accepted_on_the_first_attempt():
    report = _report()
    # cites only numbers present in the table (1 concluída, 90%)
    result = generate_narrative(lambda prompt: "1 spec concluída com first-run de 90%.", report)
    assert result.faithful is True
    assert result.attempts == 1
    assert result.divergences == ()


def test_an_invented_number_triggers_regeneration_then_succeeds():
    report = _report()
    calls = []

    def complete(prompt: str) -> str:
        calls.append(prompt)
        # first attempt invents 97%, second (seeing the error) fixes it
        return "aproveitamento de 97%." if len(calls) == 1 else "1 spec concluída."

    result = generate_narrative(complete, report, max_attempts=2)

    assert result.faithful is True
    assert result.attempts == 2
    # the regeneration prompt names the offending number
    assert "97%" in calls[1]


def test_persistently_invented_numbers_end_unfaithful():
    report = _report()
    result = generate_narrative(lambda p: "taxa mágica de 123%.", report, max_attempts=2)

    assert result.faithful is False
    assert result.attempts == 2
    assert "123%" in result.divergences
