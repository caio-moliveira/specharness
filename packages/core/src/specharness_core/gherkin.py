"""A tiny pure Gherkin parser for the subset specharness uses (SPEC-010).

The Readiness Gate needs the scenario/step structure of the `Spec:` Gherkin
blocks — enough to count `Quando` steps and scan step text for ambiguous terms.
This is a pure mirror of the subset we author (pt-BR keywords), kept in the core
with no external parser (same philosophy as `trailers.py`): what we write is a
controlled grammar, so a self-contained parser is honest and dependency-free.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Step keywords, longest first so "E"/"Mas" never shadow "Então".
_STEP_KEYWORDS = ("Quando", "Então", "Entao", "Dado", "Mas", "E")
_LANGUAGE_RE = re.compile(r"#\s*language:\s*(?P<lang>\S+)")


@dataclass(frozen=True)
class Step:
    keyword: str  # normalizado: Dado | Quando | Então | E | Mas
    text: str


@dataclass(frozen=True)
class Scenario:
    title: str
    steps: tuple[Step, ...]

    @property
    def when_steps(self) -> tuple[Step, ...]:
        return tuple(step for step in self.steps if step.keyword == "Quando")

    @property
    def step_text(self) -> str:
        return " ".join(step.text for step in self.steps)


@dataclass(frozen=True)
class Feature:
    language: str | None
    scenarios: tuple[Scenario, ...]


def parse_feature(block: str) -> Feature:
    """Parse one ```gherkin block into a `Feature` (pt-BR subset)."""
    language: str | None = None
    scenarios: list[Scenario] = []
    title: str | None = None
    steps: list[Step] = []

    def flush() -> None:
        if title is not None:
            scenarios.append(Scenario(title=title, steps=tuple(steps)))

    for raw in block.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            match = _LANGUAGE_RE.match(line)
            if match:
                language = match.group("lang")
            continue
        if line.startswith("Funcionalidade:") or line.startswith("Funcionalidade :"):
            continue
        if line.startswith("Cenário:") or line.startswith("Cenario:"):
            flush()
            title = line.split(":", 1)[1].strip()
            steps = []
            continue
        step = _parse_step(line)
        if step is not None and title is not None:
            steps.append(step)

    flush()
    return Feature(language=language, scenarios=tuple(scenarios))


def _parse_step(line: str) -> Step | None:
    for keyword in _STEP_KEYWORDS:
        if line == keyword or line.startswith(keyword + " "):
            text = line[len(keyword) :].strip()
            normalized = "Então" if keyword in ("Então", "Entao") else keyword
            return Step(keyword=normalized, text=text)
    return None
