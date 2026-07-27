"""Eval runner — the gate of the gate (SPEC-011, critério 4, métrica 1).

Validates each task's structure, then runs the golden dataset against every
reachable model in its config.yaml, failing the CI if the in-range rate drops
below pass_criteria. Unreachable models (no key, or Ollama down) are skipped
honestly — CI stays green because the call didn't run, not because it faked one.
Local models (qwen3:8b) run in dev; the API models run in CI.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import yaml

from .gate_eval import (
    in_range_rate,
    meets_criteria,
    parse_golden,
    reachable_models,
    score_in_range,
)

EVALS_ROOT = Path(__file__).resolve().parents[1]

#: (model, spec_text) -> score. Overridable in tests.
Evaluator = Callable[[str, str], int]


def _real_evaluator(model: str, spec_text: str) -> int:
    from specharness_adapters.llm import evaluate_spec
    from specharness_adapters.llm.client import LiteLlmClient
    from specharness_core.ports.llm import resolve_model_target

    client = LiteLlmClient(resolve_model_target(model, os.environ), os.environ)
    return evaluate_spec(spec_text, client).score


def run(
    env: Mapping[str, str] | None = None,
    *,
    evaluator: Evaluator = _real_evaluator,
    ollama_up: bool | None = None,
) -> int:
    resolved = os.environ if env is None else env
    if ollama_up is None:
        from specharness_adapters.llm import ollama_responds
        from specharness_core.ports.llm import DEFAULT_OLLAMA_BASE_URL, OLLAMA_BASE_URL_ENV

        base = resolved.get(OLLAMA_BASE_URL_ENV, "").strip() or DEFAULT_OLLAMA_BASE_URL
        ollama_up = ollama_responds(base)

    tasks = [p for p in EVALS_ROOT.iterdir() if p.is_dir() and p.name != "runner"]
    if not tasks:
        print("Nenhuma task de eval encontrada.")
        return 1

    failures = 0
    for task in sorted(tasks):
        failures += _run_task(task, resolved, evaluator, ollama_up=ollama_up)
    if failures:
        print(f"\n{failures} verificação(ões) de eval falharam.")
        return 1
    print("\n✓ Evals ok.")
    return 0


def _run_task(task: Path, env: Mapping[str, str], evaluator: Evaluator, *, ollama_up: bool) -> int:
    config_path = task / "config.yaml"
    golden_dir = task / "golden"
    if not (config_path.exists() and (task / "rubric.md").exists() and golden_dir.exists()):
        print(f"[INCOMPLETA] {task.name}: falta config.yaml, rubric.md ou golden/")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    goldens = [
        parse_golden(p.name, p.read_text(encoding="utf-8")) for p in sorted(golden_dir.glob("*.md"))
    ]
    if not goldens:
        print(f"[INCOMPLETA] {task.name}: sem goldens")
        return 1

    models = reachable_models(config.get("models", []), env, ollama_up=ollama_up)
    if not models:
        print(f"[ok] {task.name}: {len(goldens)} goldens; sem modelo alcançável, execução pulada")
        return 0

    pass_criteria = config.get("pass_criteria", {})
    failures = 0
    for model in models:
        hits = [score_in_range(evaluator(model, g.spec_text), g.expected_range) for g in goldens]
        rate = in_range_rate(hits)
        ok = meets_criteria(rate, pass_criteria)
        mark = "ok" if ok else "FAIL"
        print(
            f"[{mark}] {task.name} · {model}: {rate:.0%} dentro da faixa ({sum(hits)}/{len(hits)})"
        )
        failures += 0 if ok else 1
    return failures


if __name__ == "__main__":
    sys.exit(run())
