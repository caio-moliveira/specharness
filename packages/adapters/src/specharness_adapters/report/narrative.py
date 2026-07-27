"""LLM narrative for the sprint report (SPEC-015, ADR-006).

The prose is the only part the LLM writes, and it is kept honest by the core's
read-before-cite guard: after each generation, `narrative_divergences` checks that
every number cited exists in the tabular data. A narrative that invents a number is
rejected and regenerated with the offending numbers pointed out — up to a bounded
number of attempts. `complete` is any text-completion callable (the SPEC-005
`LiteLlmClient.complete`), so this is driven hermetically in tests.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from specharness_core.report import SprintReport, narrative_divergences, render_markdown

Complete = Callable[[str], str]


@dataclass(frozen=True)
class NarrativeResult:
    """The outcome of a narrative generation attempt loop."""

    text: str
    faithful: bool
    attempts: int
    divergences: tuple[str, ...]


def _prompt(report: SprintReport, offending: tuple[str, ...]) -> str:
    base = (
        "Escreva uma narrativa curta (3-5 frases) da sprint com base EXCLUSIVAMENTE "
        "na tabela abaixo. Só cite números que aparecem na tabela; não invente valores.\n\n"
        f"{render_markdown(report)}\n"
    )
    if offending:
        base += (
            "\nA tentativa anterior citou números que não existem na tabela: "
            f"{', '.join(offending)}. Reescreva usando apenas números da tabela.\n"
        )
    return base


def generate_narrative(
    complete: Complete, report: SprintReport, *, max_attempts: int = 2
) -> NarrativeResult:
    """Generate a narrative, regenerating while it cites numbers not in the data."""
    offending: tuple[str, ...] = ()
    text = ""
    for attempt in range(1, max_attempts + 1):
        text = complete(_prompt(report, offending))
        divergences = tuple(narrative_divergences(text, report))
        if not divergences:
            return NarrativeResult(text=text, faithful=True, attempts=attempt, divergences=())
        offending = divergences
    return NarrativeResult(text=text, faithful=False, attempts=max_attempts, divergences=offending)
