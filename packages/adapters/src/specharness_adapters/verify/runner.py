"""Run a spec's scenarios against a step registry (SPEC-012, ADR-018).

Per scenario: a step with no matching definition makes the whole scenario
`pending` (distinct from a failure — critério 4); a step callable that raises
makes it `failed`; all steps passing makes it `passed`.
"""

from __future__ import annotations

from collections.abc import Iterator

from specharness_core.gherkin import Scenario, parse_feature
from specharness_core.specschema import ParsedSpec
from specharness_core.verify import ScenarioStatus

from .registry import StepRegistry


def scenarios_of(parsed: ParsedSpec) -> Iterator[Scenario]:
    """Every scenario declared in the spec's ```gherkin blocks."""
    for block in parsed.gherkin_blocks:
        yield from parse_feature(block).scenarios


def run_scenario(scenario: Scenario, registry: StepRegistry) -> ScenarioStatus:
    if not scenario.steps:
        return "pending"
    for step in scenario.steps:
        fn = registry.find(step.text)
        if fn is None:
            return "pending"  # step sem definição -> pendência, não falha
        try:
            fn()
        except Exception:
            return "failed"
    return "passed"


def run_spec(parsed: ParsedSpec, registry: StepRegistry) -> list[tuple[str, ScenarioStatus]]:
    """Run every scenario, returning (título, status) in declaration order."""
    return [(scenario.title, run_scenario(scenario, registry)) for scenario in scenarios_of(parsed)]
