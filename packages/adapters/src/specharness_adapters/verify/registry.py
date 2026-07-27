"""Step registry — the minimal BDD runner's core (SPEC-012, ADR-018).

A repo registers step definitions (regex pattern -> callable) into a
`StepRegistry`; the runner resolves each Gherkin step's text against it. No
pytest-bdd, no feature files (ADR-018) — a self-contained matcher over the pure
Gherkin parser.
"""

from __future__ import annotations

import re
from collections.abc import Callable

StepFn = Callable[[], None]


class StepRegistry:
    """Maps step text patterns to callables. First match wins."""

    def __init__(self) -> None:
        self._steps: list[tuple[re.Pattern[str], StepFn]] = []

    def register(self, pattern: str, fn: StepFn) -> None:
        self._steps.append((re.compile(pattern), fn))

    def step(self, pattern: str) -> Callable[[StepFn], StepFn]:
        """Decorator form: `@registry.step("um commit com trailer")`."""

        def decorator(fn: StepFn) -> StepFn:
            self.register(pattern, fn)
            return fn

        return decorator

    def find(self, text: str) -> StepFn | None:
        for pattern, fn in self._steps:
            if pattern.search(text):
                return fn
        return None
