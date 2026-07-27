"""Golden-dataset scoring for the Readiness Gate eval (SPEC-011, métrica 1).

Pure helpers, so the pass/fail logic is testable without a model: parse a golden
(expected score range + embedded spec), decide if a score lands in range, and
aggregate the in-range rate against the task's pass_criteria.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

import yaml

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
# Greedy + end-anchored so a spec whose body itself contains a ```gherkin fence
# is captured whole, not truncated at the inner fence.
_FENCE_RE = re.compile(r"```(?:markdown|md)?\s*\n(.*)\n```\s*\Z", re.DOTALL)


@dataclass(frozen=True)
class Golden:
    name: str
    expected_range: tuple[int, int]
    spec_text: str


def parse_golden(name: str, text: str) -> Golden:
    """Parse a golden file: frontmatter `expected_range` + the embedded spec."""
    match = _FRONTMATTER_RE.match(text)
    if match is None:
        raise ValueError(f"golden {name} sem frontmatter")
    meta = yaml.safe_load(match.group(1)) or {}
    raw_range = meta.get("expected_range")
    if not (isinstance(raw_range, list) and len(raw_range) == 2):
        raise ValueError(f"golden {name} sem expected_range [min, max]")
    body = match.group(2)
    fenced = _FENCE_RE.search(body)
    spec_text = fenced.group(1).strip() if fenced else body.strip()
    return Golden(
        name=name, expected_range=(int(raw_range[0]), int(raw_range[1])), spec_text=spec_text
    )


def score_in_range(score: int, expected: tuple[int, int]) -> bool:
    return expected[0] <= score <= expected[1]


def in_range_rate(hits: list[bool]) -> float:
    return sum(hits) / len(hits) if hits else 0.0


def meets_criteria(rate: float, pass_criteria: Mapping[str, float]) -> bool:
    required = float(pass_criteria.get("score_in_range_rate", 0.9))
    return rate >= required


def reachable_models(models: list[str], env: Mapping[str, str], *, ollama_up: bool) -> list[str]:
    """Which configured models can actually be called now (opt-in, skip-honest).

    API models need their key in the environment; local Ollama models need a
    server answering. Unreachable models are skipped, not failed.
    """
    from specharness_core.ports.llm import (
        ANTHROPIC_API_KEY_ENV,
        AZURE_API_KEY_ENV,
        OPENAI_API_KEY_ENV,
    )

    key_for = {
        "anthropic": ANTHROPIC_API_KEY_ENV,
        "openai": OPENAI_API_KEY_ENV,
        "azure": AZURE_API_KEY_ENV,
    }
    out: list[str] = []
    for model in models:
        provider = model.split("/", 1)[0]
        if provider == "ollama":
            if ollama_up:
                out.append(model)
        elif env.get(key_for.get(provider, ""), "").strip():
            out.append(model)
    return out
