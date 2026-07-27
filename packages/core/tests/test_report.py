"""Pure sprint report (SPEC-015): assembly, markdown and the read-before-cite guard."""

from __future__ import annotations

from specharness_core import (
    SprintReport,
    build_report,
    extract_numbers,
    is_faithful,
    narrative_divergences,
    render_markdown,
    report_lines,
)
from specharness_core.linking import LinkingResult
from specharness_core.metrics import SpecMetrics, SprintSnapshot
from specharness_core.perception import SprintPerception


def _perception(gap=0.25) -> SprintPerception:
    return SprintPerception(
        sprint="2026-A4",
        n_samples=3,
        n_skipped=1,
        aproveitamento_mean=4.0,
        retrabalho_dist={"nenhum": 1, "leve": 2, "pesado": 0},
        tempo_dist={"economizou": 2, "neutro": 1, "custou": 0},
        perception_gap=gap,
    )


def _snapshot() -> SprintSnapshot:
    return SprintSnapshot(
        "2026-A4",
        (
            SpecMetrics("SPEC-013", 360000.0, 0.9, 2, 0.1, 0.2, 1.0, 1.5, commits=8),
            SpecMetrics("SPEC-014", None, None, None, None, None, None, None, commits=0),
        ),
    )


_UNSET = object()


def _report(snapshot=_UNSET, statuses=None, linking=None, perception=None) -> SprintReport:
    return build_report(
        "2026-A4",
        _snapshot() if snapshot is _UNSET else snapshot,
        perception or _perception(),
        linking or LinkingResult((), (), ()),
        statuses or {"SPEC-013": "done", "SPEC-014": "verifying"},
    )


# --- assembly ---------------------------------------------------------------


def test_planned_vs_concluded_counts():
    report = _report(statuses={"SPEC-013": "done", "SPEC-014": "verifying", "SPEC-015": "done"})
    assert report.n_planejadas == 3
    assert report.n_concluidas == 2


def test_rows_join_status_with_metrics_and_null_when_absent():
    report = _report()
    by_id = {r.spec_id: r for r in report.rows}
    assert by_id["SPEC-013"].first_run_pass_rate == 0.9
    assert by_id["SPEC-013"].commits == 8
    # SPEC-014 has a metrics row of all-None
    assert by_id["SPEC-014"].cycle_time_seconds is None


def test_a_spec_without_any_metrics_row_is_null_not_crash():
    # snapshot only has SPEC-013; SPEC-099 is planned but never measured
    report = _report(statuses={"SPEC-013": "done", "SPEC-099": "ready"})
    row = next(r for r in report.rows if r.spec_id == "SPEC-099")
    assert row.commits == 0 and row.first_run_pass_rate is None


def test_report_without_a_snapshot_still_builds():
    report = _report(snapshot=None, statuses={"SPEC-013": "done"})
    assert report.rows[0].cycle_time_seconds is None
    assert report.n_concluidas == 1


def test_orphans_come_from_the_linking_result():
    linking = LinkingResult((), ("deadbeef",), ("SPEC-050",))
    report = _report(linking=linking)
    assert report.orphan_commits == ("deadbeef",)
    assert report.orphan_specs == ("SPEC-050",)


# --- markdown ---------------------------------------------------------------


def test_markdown_has_the_headline_sections_and_rows():
    md = render_markdown(_report())
    assert "# Relatório da sprint 2026-A4" in md
    assert "Specs planejadas: 2" in md
    assert "Specs concluídas: 1" in md
    assert "| SPEC-013 |" in md
    assert "## Percepção" in md
    assert report_lines(_report())[0] == "# Relatório da sprint 2026-A4"


# --- read-before-cite guard -------------------------------------------------


def test_extract_numbers_finds_integers_decimals_and_percents():
    assert extract_numbers("3 specs, 90% e 1.5h") == {"3", "90%", "1.5"}


def test_a_faithful_narrative_passes():
    report = _report()
    # every number below appears in the rendered table (2 planejadas, 1 concluída, 90%)
    narrative = "A sprint teve 2 specs planejadas e 1 concluída, com first-run de 90%."
    assert narrative_divergences(narrative, report) == []
    assert is_faithful(narrative, report)


def test_an_invented_number_is_flagged():
    report = _report()
    narrative = "A taxa de aproveitamento foi de 97% em toda a sprint."
    divergences = narrative_divergences(narrative, report)
    assert "97%" in divergences
    assert not is_faithful(narrative, report)
