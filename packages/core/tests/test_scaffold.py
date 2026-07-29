"""Scaffolding do harness (SPEC-023) — lógica pura."""

from __future__ import annotations

import subprocess

import pytest
from specharness_core import parse_spec
from specharness_core.onboarding import OPTIONS
from specharness_core.scaffold import (
    AGENT_LAYER_FILE,
    FIXED_SPINE,
    SEED_SPEC_FILE,
    ScaffoldParams,
    render_agents_md,
    render_commit_msg_hook,
    render_spec_template,
    scaffold_files,
)


def test_fixed_spine_present_for_any_agent_and_tracker():
    # A espinha fixa não é desligável: aparece em TODA combinação (cenário SPEC-023).
    for agent in OPTIONS["agent"]:
        for tracker in OPTIONS["tracker"]:
            agents_md = scaffold_files(agent, tracker, ScaffoldParams())["AGENTS.md"]
            for marker in FIXED_SPINE:
                assert marker in agents_md, f"{marker!r} sumiu para {agent}/{tracker}"


def test_each_agent_gets_its_layer_file():
    for agent, filename in AGENT_LAYER_FILE.items():
        files = scaffold_files(agent, "jira", ScaffoldParams())
        assert filename in files  # camada específica do agente
        assert "AGENTS.md" in files  # base comum sempre presente


def test_params_flow_into_agents_md():
    md = render_agents_md("jira", ScaffoldParams(coverage_min=90, commit_convention="gitmoji"))
    assert "90%" in md
    assert "gitmoji" in md


def test_work_pickup_is_declared():
    md = render_agents_md("jira", ScaffoldParams())
    assert "ready" in md
    assert "tracker" in md.lower()


def test_unknown_agent_is_rejected():
    with pytest.raises(ValueError):
        scaffold_files("cursor", "jira", ScaffoldParams())


def test_commit_hook_blocks_without_trailer_and_passes_with(tmp_path):
    hook = tmp_path / "commit-msg"
    hook.write_text(render_commit_msg_hook(), encoding="utf-8")
    bad = tmp_path / "bad.txt"
    bad.write_text("feat: sem trailer\n", encoding="utf-8")
    good = tmp_path / "good.txt"
    good.write_text("feat: com trailer\n\nSpec: SPEC-001\n", encoding="utf-8")

    assert subprocess.run(["sh", str(hook), str(bad)]).returncode == 1
    assert subprocess.run(["sh", str(hook), str(good)]).returncode == 0


def test_seed_spec_is_schema_valid():
    # A métrica "arquivos gerados passam no schema" precisa de um artefato que o
    # schema DE FATO valide — a spec-semente.
    parsed = parse_spec(render_spec_template())  # não levanta => válido
    assert parsed.spec_id == "SPEC-000"
    assert parsed.gherkin_blocks  # traz cenário BDD


def test_scaffold_includes_seed_spec():
    assert SEED_SPEC_FILE in scaffold_files("claude-code", "jira", ScaffoldParams())
