"""Minimal internal BDD runner for `specharness verify` (SPEC-012, ADR-018).

This is where importing and executing the repo's step definitions (I/O) is
allowed. The core knows only what a scenario run is and when it blocks `done`;
this package resolves and runs the steps.
"""

from .loader import VerifyError, load_steps
from .registry import StepRegistry
from .runner import run_scenario, run_spec, scenarios_of

__all__ = [
    "StepRegistry",
    "VerifyError",
    "load_steps",
    "run_scenario",
    "run_spec",
    "scenarios_of",
]
