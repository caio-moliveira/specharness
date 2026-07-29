"""Scaffolding do harness (SPEC-023) — lógica pura."""

from __future__ import annotations

import subprocess

import pytest
from specharness_core import parse_spec
from specharness_core.onboarding import OPTIONS
from specharness_core.scaffold import (
    AGENT_LAYER_FILE,
    BLOCK_BEGIN,
    BLOCK_END,
    FIXED_SPINE,
    SEED_SPEC_FILE,
    ScaffoldParams,
    block_files,
    merge_block,
    render_agent_layer,
    render_agents_md,
    render_commit_msg_hook,
    render_spec_template,
    render_specs_readme,
    starter_files,
    wrap_block,
)


def test_fixed_spine_present_for_any_agent_and_tracker():
    # A espinha fixa não é desligável: aparece em TODA combinação (cenário SPEC-023).
    for agent in OPTIONS["agent"]:
        for tracker in OPTIONS["tracker"]:
            agents_md = block_files(agent, tracker, ScaffoldParams())["AGENTS.md"]
            for marker in FIXED_SPINE:
                assert marker in agents_md, f"{marker!r} sumiu para {agent}/{tracker}"


#: Ferramentas/caminhos do NOSSO fluxo de dev (produto A) que o init NÃO provisiona
#: no repo do usuário (produto B) — não podem aparecer no harness gerado (SPEC-026).
#: `profiles` cru (sem barra) também é proibido: pega qualquer citação do diretório.
_UNPROVISIONED_INTERNAL_REFS = ("verificar-spec", "profiles")


def test_generated_harness_references_no_unprovisioned_internal_tooling():
    # O harness gerado expressa o método, sem citar ferramenta/caminho que só
    # existe no repositório do specharness — nos TRÊS renderers (SPEC-026).
    for agent in OPTIONS["agent"]:
        for tracker in OPTIONS["tracker"]:
            generated = "\n".join(
                (
                    *block_files(agent, tracker, ScaffoldParams()).values(),
                    render_specs_readme(tracker),
                )
            )
            for ref in _UNPROVISIONED_INTERNAL_REFS:
                assert ref not in generated, f"{ref!r} vazou no harness de {agent}/{tracker}"


def test_independent_verification_survives_as_method_not_tool_name():
    # O princípio (verificação independente em contexto limpo) permanece na espinha
    # fixa, mesmo sem o nome da ferramenta interna (SPEC-026).
    md = render_agents_md("jira", ScaffoldParams())
    assert "verificação independente" in md
    assert "verificar-spec" not in md


def test_tracker_none_never_shows_the_raw_literal():
    # Com tracker none, os três renderers descrevem o backlog local em specs/, sem
    # exibir o literal cru `none` ao usuário (SPEC-026).
    rendered = (
        render_agents_md("none", ScaffoldParams()),
        render_agent_layer("claude-code", "none"),
        render_specs_readme("none"),
    )
    for text in rendered:
        assert "none" not in text
        assert "specs" in text  # aponta o backlog local


def test_each_agent_gets_its_layer_file():
    for agent, filename in AGENT_LAYER_FILE.items():
        files = block_files(agent, "jira", ScaffoldParams())
        assert filename in files  # camada específica do agente
        assert "AGENTS.md" in files  # base comum sempre presente


def test_merge_block_creates_appends_and_updates_in_place():
    block = wrap_block("HARNESS")
    # arquivo ausente → só o bloco
    assert BLOCK_BEGIN in merge_block(None, block)
    # conteúdo do usuário sem bloco → anexa, preservando o original
    merged = merge_block("MEU CONTEÚDO\n", block)
    assert "MEU CONTEÚDO" in merged and BLOCK_BEGIN in merged
    # já tem bloco → atualiza no lugar, sem duplicar
    updated = merge_block(merged, wrap_block("NOVO"))
    assert "MEU CONTEÚDO" in updated
    assert updated.count(BLOCK_BEGIN) == 1
    assert "NOVO" in updated and "HARNESS" not in updated
    assert BLOCK_END in updated


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
        block_files("cursor", "jira", ScaffoldParams())


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
    assert SEED_SPEC_FILE in starter_files("jira", ScaffoldParams())
