"""Step definitions da SPEC-017 para o gate de BDD (SPEC-012, ADR-018).

Uso: `specharness verify SPEC-017 --steps specs/steps/spec_017_steps.py`.
Três funcionalidades: veredito consolidado do ready, diagnóstico causal do
gap de percepção e listagem de órfãos no track. Os passos rodam a CLI real
via CliRunner em diretórios temporários com SQLite próprio; a camada LLM do
ready é substituída no módulo da CLI (mesmo padrão de tests/test_ready.py).
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from specharness_adapters.db import (
    MetricSnapshotStore,
    RepositoryStore,
    SqlAlchemyDatabaseGateway,
)
from specharness_adapters.verify import StepRegistry
from specharness_cli import main
from specharness_core import Evaluation, SpecMetrics, SprintSnapshot
from specharness_core.ports.database import DATABASE_URL_ENV, resolve_database_target
from specharness_core.ports.repository import Commit, PullRequest
from typer.testing import CliRunner

registry = StepRegistry()

_state: dict[str, Any] = {}


def _spec_doc(*, floor_passes: bool) -> str:
    acceptance = (
        'acceptance: ["Commit com trailer válido é vinculado à spec"]\n'
        if floor_passes
        else "acceptance: []\n"
    )
    return (
        "---\n"
        "spec: SPEC-042\n"
        'title: "T"\n'
        "status: approved\n"
        "type: feature\n"
        'success_metrics: ["linking em < 500ms"]\n' + acceptance + "---\n\n"
        "```gherkin\n"
        "# language: pt\n"
        "Funcionalidade: linking\n\n"
        "  Cenário: trailer válido vincula\n"
        "    Dado um commit com trailer\n"
        "    Quando o track roda\n"
        "    Então o commit é vinculado à spec\n"
        "```\n"
    )


def _last_line(output: str) -> str:
    return [line for line in output.splitlines() if line.strip()][-1]


# --- Funcionalidade: veredito consolidado do ready ---------------------------


def _prepare_ready(*, floor_passes: bool, providers: bool, score: int | None) -> None:
    _state.clear()
    _state["ready_doc"] = _spec_doc(floor_passes=floor_passes)
    _state["providers"] = providers
    _state["score"] = score
    _state["args"] = ["ready", "SPEC-042"]


def _run_ready() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="spec017-ready-"))
    (tmp / "specs").mkdir()
    (tmp / "specs" / "SPEC-042-t.md").write_text(_state["ready_doc"], "utf-8")
    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    originals = (main.detect_providers, main.evaluate_spec)
    providers = ["anthropic"] if _state["providers"] else []
    score = _state["score"]

    def fake_evaluate(text: str, client: Any) -> Evaluation:
        return Evaluation(score=score, issues=(), model="fake/model", cost_usd=0.0, cached=False)

    main.detect_providers = lambda env: providers
    if score is not None:
        main.evaluate_spec = fake_evaluate
    try:
        os.chdir(tmp)
        result = CliRunner().invoke(main.app, _state["args"])
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        os.chdir(saved_cwd)
        main.detect_providers, main.evaluate_spec = originals
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


@registry.step(r"uma spec que reprova no piso determinístico do Readiness Gate")
def _given_floor_failing_spec() -> None:
    _prepare_ready(floor_passes=False, providers=True, score=None)


@registry.step(r"um ambiente sem nenhum provedor LLM configurado")
def _given_no_llm_provider() -> None:
    _prepare_ready(floor_passes=True, providers=False, score=None)


@registry.step(r"uma spec que passa no piso determinístico e na camada LLM")
def _given_spec_passing_both_layers() -> None:
    _prepare_ready(floor_passes=True, providers=True, score=95)


@registry.step(r"uma spec cuja avaliação LLM fica abaixo do limiar")
def _given_spec_below_threshold() -> None:
    _prepare_ready(floor_passes=True, providers=True, score=10)


@registry.step(r"um override registrado com autor e justificativa")
def _given_override() -> None:
    _prepare_ready(floor_passes=True, providers=False, score=None)
    _state["args"] = ["ready", "SPEC-042", "--override", "--author", "tl", "--reason", "prazo"]


@registry.step(r"uma spec avaliada pelo Readiness Gate")
def _given_spec_for_json() -> None:
    _prepare_ready(floor_passes=True, providers=True, score=95)
    _state["args"] = ["ready", "SPEC-042", "--json"]


@registry.step(r"o ready roda sobre ela")
def _when_ready_runs() -> None:
    _run_ready()


@registry.step(r"o ready roda sobre uma spec que passa no piso determinístico")
def _when_ready_runs_on_passing_floor() -> None:
    _run_ready()


@registry.step(r"o ready roda com a opção de override")
def _when_ready_runs_with_override() -> None:
    _run_ready()


@registry.step(r"o ready roda com --json")
def _when_ready_runs_json() -> None:
    _run_ready()


@registry.step(r"a saída termina com \"Veredito: BLOQUEADA\" e o número de bloqueadores")
def _then_blocked_with_count() -> None:
    last = _last_line(_state["output"])
    assert last.startswith("Veredito: BLOQUEADA"), _state["output"]
    assert "bloqueador" in last, last


@registry.step(
    r"o aviso de camada semântica pendente permanece e a saída termina com "
    r"\"Veredito: BLOQUEADA\" citando a camada semântica"
)
def _then_blocked_citing_semantic_layer() -> None:
    assert "Camada semântica pendente" in _state["output"], _state["output"]
    last = _last_line(_state["output"])
    assert last.startswith("Veredito: BLOQUEADA"), _state["output"]
    assert "semântica" in last, last


@registry.step(r"a saída termina com \"Veredito: PRONTA\" citando o override")
def _then_ready_citing_override() -> None:
    last = _last_line(_state["output"])
    assert last.startswith("Veredito: PRONTA"), _state["output"]
    assert "override" in last, last


@registry.step(r"a saída termina com \"Veredito: PRONTA\"")
def _then_ready_verdict() -> None:
    last = _last_line(_state["output"])
    assert last.startswith("Veredito: PRONTA"), _state["output"]
    assert _state["exit_code"] == 0


@registry.step(r"a saída termina com \"Veredito: BLOQUEADA\" citando o score e o limiar")
def _then_blocked_citing_score() -> None:
    last = _last_line(_state["output"])
    assert last.startswith("Veredito: BLOQUEADA"), _state["output"]
    assert "score" in last and "limiar" in last, last


@registry.step(r"a saída é um JSON com verdict, motivo, resultado do piso e da camada LLM")
def _then_json_verdict() -> None:
    payload = json.loads(_last_line(_state["output"]))
    assert payload["verdict"] in {"ready", "blocked"}, payload
    assert "reason" in payload and "floor" in payload and "llm" in payload, payload
    assert payload["floor"]["passed"] is True
    assert payload["llm"]["score"] == 95


# --- Funcionalidade: diagnóstico do gap de percepção -------------------------


_PERCEPTION_SPEC = (
    "---\n"
    "spec: SPEC-042\n"
    'title: "P"\n'
    "status: verifying\n"
    "type: feature\n"
    "sprint: 2026-A4\n"
    'success_metrics: ["m < 1s"]\n'
    'acceptance: ["a"]\n'
    "---\n\n## Contexto\n"
)


def _perception_env() -> Any:
    """Banco sintético com PR #7 vinculado à SPEC-042 (âncora do survey)."""
    tmp = Path(tempfile.mkdtemp(prefix="spec017-perc-"))
    (tmp / "specs").mkdir()
    (tmp / "specs" / "SPEC-042-p.md").write_text(_PERCEPTION_SPEC, "utf-8")
    target = resolve_database_target({DATABASE_URL_ENV: ""}, project_root=tmp)
    SqlAlchemyDatabaseGateway(target).migrate()
    RepositoryStore(target).sync(
        "acme/tool",
        [Commit("a", "Ana", datetime(2026, 7, 27), "m", ("SPEC-042",))],
        [PullRequest(7, "t", "merged", "feat", "main", ("a",))],
    )
    _state.clear()
    _state["tmp"] = tmp
    _state["target"] = target
    return target


def _invoke_in_env(args: list[str]) -> Any:
    saved_cwd = os.getcwd()
    saved_db = os.environ.pop(DATABASE_URL_ENV, None)
    try:
        os.chdir(_state["tmp"])
        return CliRunner().invoke(main.app, args)
    finally:
        os.chdir(saved_cwd)
        if saved_db is not None:
            os.environ[DATABASE_URL_ENV] = saved_db


def _survey() -> None:
    result = _invoke_in_env(
        [
            "survey",
            "acme/tool#7",
            "--runtime",
            "R",
            "--model",
            "M",
            "--aproveitamento",
            "4",
            "--retrabalho",
            "leve",
            "--tempo",
            "custou",
        ]
    )
    assert result.exit_code == 0, result.output


@registry.step(r"uma sprint sem nenhuma amostra de percepção")
def _given_no_samples() -> None:
    _perception_env()


@registry.step(r"uma sprint com amostras de percepção e nenhum snapshot de métricas")
def _given_samples_without_snapshot() -> None:
    _perception_env()
    _survey()


@registry.step(r"um snapshot cujas specs não têm cycle time")
def _given_snapshot_without_cycle_time() -> None:
    target = _perception_env()
    _survey()
    MetricSnapshotStore(target).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-042", None, None, None, None, None, None, None, 1),),
        ),
        datetime(2026, 7, 27),
    )


@registry.step(r"amostras de percepção cujas specs não aparecem com cycle time no snapshot")
def _given_samples_not_comparable() -> None:
    target = _perception_env()
    _survey()
    MetricSnapshotStore(target).record(
        SprintSnapshot(
            "2026-A4",
            (SpecMetrics("SPEC-777", 100.0, None, None, None, None, None, None, 1),),
        ),
        datetime(2026, 7, 27),
    )


@registry.step(r"o perception roda")
def _when_perception_runs() -> None:
    result = _invoke_in_env(["perception", "2026-A4"])
    _state["output"] = result.output
    _state["exit_code"] = result.exit_code


@registry.step(r"a dica de gap indisponível manda coletar com specharness survey")
def _then_hint_points_to_survey() -> None:
    assert "Gap indisponível" in _state["output"], _state["output"]
    assert "specharness survey" in _state["output"], _state["output"]


@registry.step(r"a dica de gap indisponível manda rodar specharness metrics")
def _then_hint_points_to_metrics() -> None:
    assert "Gap indisponível" in _state["output"], _state["output"]
    assert "specharness metrics" in _state["output"], _state["output"]


@registry.step(
    r"a dica explica que faltam transições ready até done no histórico e "
    r"que recalcular métricas não muda o resultado"
)
def _then_hint_names_cycle_time_cause() -> None:
    out = _state["output"]
    assert "Gap indisponível" in out, out
    assert "cycle time" in out, out
    assert "não muda isso" in out, out
    assert "specharness metrics" not in out, out  # a dica antiga mandava para cá


@registry.step(r"a dica explica que nenhuma amostra é de spec com cycle time conhecido")
def _then_hint_says_no_comparable_sample() -> None:
    assert "Gap indisponível" in _state["output"], _state["output"]
    assert "nenhuma amostra é de spec com cycle time conhecido" in _state["output"]


# --- Funcionalidade: listagem de órfãos no track -----------------------------


def _run_track(args: list[str]) -> None:
    originals = (main.gateway_from_env, main.RepositoryStore, main._load_spec_infos)
    commits = list(_state["commits"])

    class _FakeGateway:
        target = None

        def migrate(self) -> None:
            pass

    class _FakeStore:
        def __init__(self, target: Any) -> None:
            pass

        def all_commits(self) -> list[Commit]:
            return commits

    main.gateway_from_env = lambda: _FakeGateway()
    main.RepositoryStore = _FakeStore
    main._load_spec_infos = lambda: []
    try:
        result = CliRunner().invoke(main.app, args)
        _state["output"] = result.output
        _state["exit_code"] = result.exit_code
    finally:
        main.gateway_from_env, main.RepositoryStore, main._load_spec_infos = originals


def _orphan_commits(count: int) -> list[Commit]:
    return [
        Commit(f"orfao{i:04d}" + "x" * 31, "Ana", datetime(2026, 7, 30), "m", ())
        for i in range(count)
    ]


@registry.step(r"commits ingeridos sem trailer de spec")
def _given_orphan_commits() -> None:
    _state.clear()
    _state["commits"] = _orphan_commits(2)


@registry.step(r"mais commits órfãos do que o limite pedido")
def _given_more_orphans_than_limit() -> None:
    _state.clear()
    _state["commits"] = _orphan_commits(5)
    _state["limit"] = 2


@registry.step(r"o track roda com --orphans e um limite")
def _when_track_runs_with_limit() -> None:
    _run_track(["track", "--orphans", "--limit", str(_state["limit"])])


@registry.step(r"o track roda com --orphans")
def _when_track_runs_with_orphans() -> None:
    _run_track(["track", "--orphans"])


@registry.step(r"o track roda sem opções")
def _when_track_runs_plain() -> None:
    _run_track(["track"])


@registry.step(r"os SHAs truncados dos commits órfãos aparecem na saída")
def _then_orphan_shas_listed() -> None:
    assert "commit órfão (sem trailer" in _state["output"], _state["output"]
    assert "orfao0000" in _state["output"], _state["output"]


@registry.step(r"os órfãos aparecem apenas como contagem no relatório de higiene")
def _then_orphans_only_counted() -> None:
    assert "2 commits órfãos" in _state["output"], _state["output"]
    assert "commit órfão (sem trailer" not in _state["output"], _state["output"]


@registry.step(r"a saída lista até o limite e informa quantos ficaram de fora")
def _then_limit_respected() -> None:
    assert _state["output"].count("commit órfão (sem trailer") == _state["limit"]
    assert "e 3 outro(s)" in _state["output"], _state["output"]
