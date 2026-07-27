"""Real provider smoke test (SPEC-005, métrica 1) — opt-in, like Postgres.

The hermetic contract in `test_llm_contract.py` proves the translation logic.
This file proves a *real* call works, but only when the harness says where:
set `SPECHARNESS_TEST_LLM_MODEL` (e.g. `ollama/llama3.2`) plus whatever cred-
env that model needs. With nothing set it skips, so CI stays green by honesty,
not by a call that never ran — the same contract the Postgres half keeps.
"""

from __future__ import annotations

import os
import time

import pytest
from specharness_adapters.llm import check_connection
from specharness_core.config import RoutingConfig

TEST_MODEL_ENV = "SPECHARNESS_TEST_LLM_MODEL"
BUDGET_S = 15.0  # métrica 1: < 15s por provedor

# `reason=` fica na MESMA linha física do skipif: o gate de integridade
# (scripts/test_integrity.py) lê o diff linha-a-linha e exige o par junto.
_NO_MODEL = not os.environ.get(TEST_MODEL_ENV, "").strip()
pytestmark = pytest.mark.skipif(_NO_MODEL, reason=f"defina {TEST_MODEL_ENV} para um provedor real")


def test_a_real_call_validates_structured_output_within_budget():
    routing = RoutingConfig(default=os.environ[TEST_MODEL_ENV])

    started = time.perf_counter()
    report = check_connection(os.environ, routing=routing)
    elapsed = time.perf_counter() - started

    assert report.output  # structured output validou (senão test() teria levantado)
    assert elapsed < BUDGET_S, f"chamada levou {elapsed:.2f}s"
