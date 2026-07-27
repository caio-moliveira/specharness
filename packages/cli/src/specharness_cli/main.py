"""specharness CLI (SPEC-002 §1.2). Commands land as their specs are built."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from specharness_adapters.db import (
    MetricSnapshotStore,
    OverrideStore,
    PerceptionStore,
    ReadinessCacheStore,
    RepositoryStore,
    ScenarioRunStore,
    WorkItemStore,
    gateway_from_env,
)
from specharness_adapters.git import LocalGitCommitReader
from specharness_adapters.github import GitHubClient
from specharness_adapters.github_issues import GitHubIssuesClient
from specharness_adapters.llm import (
    PROMPT_VERSION,
    check_connection,
    client_from_env,
    detect_providers,
    evaluate_spec,
)
from specharness_adapters.metrics import (
    SprintHygieneReader,
    StatusHistoryReader,
    SurveillanceRejected,
    TurnoverReader,
    guard_query,
)
from specharness_adapters.redmine import RedmineClient
from specharness_adapters.verify import StepRegistry, VerifyError, load_steps, run_spec
from specharness_core import (
    Evaluation,
    Override,
    PerceptionError,
    PerceptionSample,
    ReadinessReport,
    ScenarioRun,
    SpecInfo,
    SpecMetrics,
    SpecParseError,
    SpecStatus,
    SprintSnapshot,
    VerifyReport,
    __version__,
    aggregate_perception,
    content_hash,
    cycle_time_seconds,
    evaluate_readiness,
    first_run_pass_rate,
    hygiene_report,
    is_ci,
    iterations_to_green,
    link_commits,
    parse_spec,
    turnover_ratio,
    validate_answers,
)
from specharness_core.config import (
    CONFIG_FILENAME,
    ConfigError,
    ReadinessConfig,
    RoutingConfig,
    TrackerConfig,
    load_readiness,
    load_routing,
    load_tracker,
)
from specharness_core.ports.database import DatabaseError
from specharness_core.ports.llm import LLMError, onboarding_status
from specharness_core.ports.repository import (
    GITHUB_TOKEN_ENV,
    AuthenticationFailed,
    RepositoryError,
)
from specharness_core.ports.tracker import (
    REDMINE_API_KEY_ENV,
    InvalidTrackerConfig,
    TrackerAuthenticationFailed,
    TrackerError,
)

app = typer.Typer(
    name="specharness",
    help="Decision, quality and metrics layer for spec-driven development.",
    no_args_is_help=True,
)
console = Console()
# Errors go to stderr unwrapped: the message names an env var and a URL, and a
# line break in the middle of either makes it harder to act on (SPEC-004).
err_console = Console(stderr=True, soft_wrap=True)

connect_app = typer.Typer(
    name="connect",
    help="Conecta o specharness aos serviços do onboarding (SPEC-001 §5.1).",
    no_args_is_help=True,
)
app.add_typer(connect_app, name="connect")

llm_app = typer.Typer(
    name="llm",
    help="Conexão LLM do onboarding — obrigatória (SPEC-005, ADR-006).",
    no_args_is_help=True,
)
app.add_typer(llm_app, name="llm")


@app.command()
def version() -> None:
    """Show specharness version."""
    console.print(f"specharness [bold]{__version__}[/bold] (Fase A)")


@app.command()
def status() -> None:
    """Overview of what is implemented in this build."""
    table = Table(title="specharness — Fase A build map")
    table.add_column("Comando")
    table.add_column("Spec")
    table.add_column("Estado")
    rows = [
        ("specharness connect db", "SPEC-004", "disponível"),
        ("specharness llm test", "SPEC-005", "disponível"),
        ("specharness connect repo", "SPEC-006", "disponível"),
        ("specharness connect tracker", "SPEC-007", "disponível"),
        ("specharness connect issues", "SPEC-008", "disponível"),
        ("specharness track", "SPEC-009", "disponível"),
        ("specharness ready <spec>", "SPEC-010/011", "disponível"),
        ("specharness verify", "SPEC-012", "disponível"),
        ("specharness metrics <sprint>", "SPEC-013", "disponível"),
        ("specharness survey / perception", "SPEC-014", "disponível"),
        ("specharness report", "SPEC-015", "planejado"),
    ]
    for row in rows:
        table.add_row(*row)
    console.print(table)


@app.command()
def track() -> None:
    """Vincula commits a specs pelo trailer e reporta órfãos (SPEC-009).

    Lê os commits já ingeridos (SPEC-006) e o registro de specs do disco, e
    calcula a visão pipeline (vínculos válidos) e o relatório de higiene
    (vínculos inválidos, commits órfãos, specs órfãs) a cada execução.
    """
    try:
        gateway = gateway_from_env()
        gateway.migrate()
        commits = RepositoryStore(gateway.target).all_commits()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    result = link_commits(commits, _load_spec_infos())
    _render_track(result)


def _load_spec_infos() -> list[SpecInfo]:
    """The spec registry, from specs/*.md on disk (SPEC-003)."""
    infos: list[SpecInfo] = []
    for path in sorted((Path.cwd() / "specs").glob("*.md")):
        try:
            parsed = parse_spec(path.read_text(encoding="utf-8"))
        except SpecParseError:
            continue  # um arquivo inválido é problema do hook de schema, não do track
        infos.append(
            SpecInfo(
                spec_id=parsed.spec_id,
                status=str(parsed.frontmatter.status),
                sprint=parsed.frontmatter.sprint,
            )
        )
    return infos


def _render_track(result) -> None:
    table = Table(title="Pipeline commit → spec")
    table.add_column("Commit")
    table.add_column("Spec")
    for link in result.valid_links:
        table.add_row(link.commit_sha[:10], link.spec_id)
    console.print(table)

    console.print(
        f"Higiene: {len(result.valid_links)} vínculos válidos · "
        f"{len(result.invalid_links)} inválidos · "
        f"{len(result.orphan_commits)} commits órfãos · "
        f"{len(result.orphan_specs)} specs órfãs.",
        markup=False,
    )
    for link in result.invalid_links:
        console.print(
            f"  ⚠ vínculo inválido: {link.commit_sha[:10]} → {link.spec_id} (spec inexistente)",
            markup=False,
        )
    for spec_id in result.orphan_specs:
        console.print(f"  ⚠ spec órfã (in_progress sem commit): {spec_id}", markup=False)
    if result.is_clean:
        console.print("✓ Pipeline limpa.", markup=False)


@app.command()
def ready(
    spec: str = typer.Argument(..., help="id ou caminho da spec (ex.: SPEC-010)"),
    override: bool = typer.Option(False, "--override", help="registra um override auditado"),
    author: str | None = typer.Option(None, "--author", help="autor do override"),
    reason: str | None = typer.Option(None, "--reason", help="justificativa do override"),
) -> None:
    """Roda o Readiness Gate sobre uma spec: piso determinístico + camada LLM.

    O piso mecânico (SPEC-010) roda primeiro; a camada LLM (SPEC-011) só avalia o
    que passou. Score abaixo do limiar bloqueia. O Tech Lead pode liberar com
    --override --author X --reason Y — o override é auditado (autor, data,
    justificativa). Spec inalterada usa cache e não reavalia.
    """
    path = _resolve_spec_path(spec)
    if path is None:
        err_console.print(f"✗ spec não encontrada: {spec}", markup=False, style="red")
        raise typer.Exit(1) from None
    text = path.read_text(encoding="utf-8")
    try:
        parsed = parse_spec(text)
    except SpecParseError as exc:
        err_console.print(f"✗ {path.name}: {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    if override:
        _record_override(parsed.spec_id, author, reason)
        return

    report = evaluate_readiness(parsed, _load_registry())
    _render_readiness(parsed.spec_id, report)
    if not report.passed:
        raise typer.Exit(1)

    if not detect_providers(os.environ):
        console.print(
            "⚠ Camada semântica pendente: nenhum provedor LLM. O piso determinístico passou.",
            markup=False,
        )
        err_console.print(f"  {onboarding_status(semantic_ready=False).guidance}", markup=False)
        raise typer.Exit(1)

    threshold = _load_readiness_config().threshold
    try:
        evaluation = _evaluate_llm(text)
    except LLMError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    _render_evaluation(parsed.spec_id, evaluation, threshold)
    if evaluation.blocks(threshold):
        raise typer.Exit(1)


def _record_override(spec_id: str, author: str | None, reason: str | None) -> None:
    if not author or not reason:
        err_console.print(
            "✗ override exige --author e --reason (autor e justificativa auditados)",
            markup=False,
            style="red",
        )
        raise typer.Exit(1) from None
    try:
        gateway = gateway_from_env()
        gateway.migrate()
        OverrideStore(gateway.target).record(
            Override(spec_id=spec_id, author=author, justification=reason, at=datetime.now().date())
        )
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    console.print(
        f"✓ Override registrado por {author}: {spec_id} liberada para ready.", markup=False
    )
    console.print(f"  Justificativa: {reason}", markup=False)


def _evaluate_llm(text: str) -> Evaluation:
    gateway = gateway_from_env()
    gateway.migrate()
    cache = ReadinessCacheStore(gateway.target)
    key = content_hash(text, PROMPT_VERSION)
    cached = cache.get(key)
    if cached is not None:
        return cached
    client = client_from_env(os.environ, routing=_load_routing(), task="readiness_gate")
    evaluation = evaluate_spec(text, client)
    cache.put(key, evaluation, datetime.now())
    return evaluation


def _load_readiness_config() -> ReadinessConfig:
    path = Path.cwd() / CONFIG_FILENAME
    if not path.is_file():
        return ReadinessConfig()
    return load_readiness(path.read_text(encoding="utf-8"))


def _render_evaluation(spec_id: str, evaluation: Evaluation, threshold: int) -> None:
    origin = "cache" if evaluation.cached else evaluation.model
    console.print(
        f"Avaliação LLM — score {evaluation.score}/100 (limiar {threshold}) · "
        f"{origin} · custo {evaluation.cost_label}",
        markup=False,
    )
    for issue in evaluation.issues:
        console.print(
            f"  • [{issue.category}] {issue.description} → {issue.suggestion}", markup=False
        )
    if evaluation.blocks(threshold):
        console.print(
            f"✗ {spec_id} bloqueada pela camada LLM (score < {threshold}). "
            "Libere com --override --author X --reason Y se for decisão do Tech Lead.",
            markup=False,
        )
    else:
        console.print(f"✓ {spec_id} passa na camada LLM.", markup=False)


def _resolve_spec_path(spec: str) -> Path | None:
    candidate = Path(spec)
    if candidate.suffix == ".md" and candidate.is_file():
        return candidate
    specs_dir = Path.cwd() / "specs"
    matches = sorted(specs_dir.glob(f"{spec}-*.md")) + sorted(specs_dir.glob(f"{spec}.md"))
    return matches[0] if matches else None


def _load_registry() -> dict[str, SpecStatus]:
    return {info.spec_id: SpecStatus(info.status) for info in _load_spec_infos()}


def _render_readiness(spec_id: str, report: ReadinessReport) -> None:
    table = Table(title=f"Matriz critério × cenário — {spec_id}")
    table.add_column("#")
    table.add_column("Critério")
    table.add_column("Coberto por")
    for row in report.matrix:
        covered = ", ".join(f"cenário {i}" for i in row.covered_by) if row.covered_by else "—"
        table.add_row(str(row.index), row.criterion, covered)
    console.print(table)

    if report.blockers:
        console.print(f"Bloqueadores ({len(report.blockers)}):", markup=False, style="red")
        for blocker in report.blockers:
            console.print(f"  ✗ [{blocker.location}] {blocker.message}", markup=False, style="red")
    if report.recommendations:
        console.print(f"Recomendações ({len(report.recommendations)}):", markup=False)
        for rec in report.recommendations:
            suffix = f" — {rec.suggestion}" if rec.suggestion else ""
            console.print(f"  • [{rec.location}] {rec.message}{suffix}", markup=False)

    if report.passed:
        console.print(f"✓ {spec_id} passa no piso determinístico do Readiness Gate.", markup=False)
    else:
        console.print(
            f"✗ {spec_id} não passa: {len(report.blockers)} bloqueador(es).", markup=False
        )


@app.command()
def verify(
    spec: str = typer.Argument(..., help="id ou caminho da spec"),
    ci: bool = typer.Option(False, "--ci", help="modo CI: marca first-run e persiste o resultado"),
    json_out: bool = typer.Option(False, "--json", help="saída legível por máquina (JSON)"),
    steps: str | None = typer.Option(None, "--steps", help="módulo Python com as step definitions"),
) -> None:
    """Executa os cenários BDD da spec e emite o veredito de done (SPEC-012).

    Cada cenário vira passou/falhou/pendente (step sem definição = pendente,
    distinto de falha). Qualquer cenário não-verde bloqueia done (exit 1). No CI
    (--ci ou CI=true) o resultado é persistido como ScenarioRun e o primeiro run
    após ready é marcado first-run; execuções locais são informativas. A
    transição para done é exclusiva do CI (ADR-016).
    """
    path = _resolve_spec_path(spec)
    if path is None:
        err_console.print(f"✗ spec não encontrada: {spec}", markup=False, style="red")
        raise typer.Exit(1) from None
    try:
        parsed = parse_spec(path.read_text(encoding="utf-8"))
    except SpecParseError as exc:
        err_console.print(f"✗ {path.name}: {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    try:
        registry = load_steps(Path(steps)) if steps else StepRegistry()
    except VerifyError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    results = run_spec(parsed, registry)
    in_ci = ci or is_ci(os.environ)
    first_run = False
    if in_ci:
        try:
            gateway = gateway_from_env()
            gateway.migrate()
            store = ScenarioRunStore(gateway.target)
            first_run = not store.has_first_run(parsed.spec_id)
            runs = [
                ScenarioRun(parsed.spec_id, title, status, first_run=first_run)
                for title, status in results
            ]
            store.record(runs, datetime.now())
        except DatabaseError as exc:
            err_console.print(f"✗ {exc}", markup=False, style="red")
            raise typer.Exit(1) from None
    else:
        runs = [ScenarioRun(parsed.spec_id, title, status) for title, status in results]

    report = VerifyReport(parsed.spec_id, tuple(runs))
    if json_out or ci:
        _emit_verify_json(report, first_run=first_run, in_ci=in_ci)
    else:
        _render_verify(report, first_run=first_run)
    raise typer.Exit(0 if report.all_green else 1)


def _emit_verify_json(report: VerifyReport, *, first_run: bool, in_ci: bool) -> None:
    payload = {
        "spec": report.spec_id,
        "verdict": "green" if report.all_green else "blocked",
        "in_ci": in_ci,
        "first_run": first_run,
        "totals": {
            "passed": len(report.passed),
            "failed": len(report.failed),
            "pending": len(report.pending),
        },
        "scenarios": [{"title": r.scenario_title, "status": r.status} for r in report.runs],
    }
    print(json.dumps(payload, ensure_ascii=False))


def _render_verify(report: VerifyReport, *, first_run: bool) -> None:
    suffix = " [first-run]" if first_run else ""
    table = Table(title=f"Verify BDD — {report.spec_id}{suffix}")
    table.add_column("Cenário")
    table.add_column("Status")
    for run in report.runs:
        table.add_row(run.scenario_title, run.status)
    console.print(table)
    console.print(
        f"Verde: {len(report.passed)} · Falhou: {len(report.failed)} · "
        f"Pendente: {len(report.pending)}",
        markup=False,
    )
    for run in report.failed:
        console.print(f"  ✗ falhou: {run.scenario_title}", markup=False, style="red")
    for run in report.pending:
        console.print(
            f"  • pendente (sem step definition): {run.scenario_title} — implemente o passo",
            markup=False,
        )
    if report.all_green:
        console.print(
            f"✓ {report.spec_id}: cenários verdes — done liberado (pelo CI).", markup=False
        )
    else:
        console.print(f"✗ {report.spec_id}: done bloqueado.", markup=False, style="red")


@app.command()
def metrics(
    sprint: str = typer.Argument(..., help="sprint a calcular (ex.: 2026-A4)"),
    repo: str = typer.Option(".", "--repo", help="raiz do repositório git"),
    specs_dir: str = typer.Option("specs", "--specs", help="diretório das specs"),
    base: str | None = typer.Option(None, "--base", help="ref base para higiene de tampering"),
    by: str | None = typer.Option(
        None, "--by", help="eixos de agregação (vírgula); indivíduo é rejeitado (ADR-008)"
    ),
    json_out: bool = typer.Option(False, "--json", help="saída legível por máquina (JSON)"),
) -> None:
    """Calcula e persiste o snapshot de métricas objetivas de uma sprint (SPEC-013).

    As métricas derivam só de artefatos brutos: cycle time vem do histórico de
    status no git, first-run e iterações de scenario_runs, turnover de git blame na
    janela — número auto-relatado por agente nunca entra (ADR-016). Snapshots são
    append-only; recalcular gera nova série. Consultas por indivíduo são recusadas
    pela política anti-vigilância (ADR-008).
    """
    dimensions = [d.strip() for d in by.split(",")] if by else []
    try:
        guard_query(dimensions)
    except SurveillanceRejected as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(2) from None

    repo_path = Path(repo)
    specs = _sprint_specs(Path(specs_dir), sprint)
    if not specs:
        err_console.print(f"✗ nenhuma spec na sprint {sprint}", markup=False, style="red")
        raise typer.Exit(1) from None

    as_of = datetime.now(UTC)
    try:
        gateway = gateway_from_env()
        gateway.migrate()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    run_store = ScenarioRunStore(gateway.target)
    snap_store = MetricSnapshotStore(gateway.target)

    try:
        turnover = TurnoverReader(repo_path)
        baseline_30 = turnover.repo_baseline(window_days=30, as_of=as_of)
        baseline_90 = turnover.repo_baseline(window_days=90, as_of=as_of)
        commits = list(LocalGitCommitReader(repo_path).commits())
        spec_metrics = tuple(
            _spec_metrics(
                spec_id,
                relpath,
                repo_path,
                run_store,
                turnover,
                commits,
                as_of,
                baseline_30,
                baseline_90,
            )
            for spec_id, relpath in specs
        )
        hygiene = tuple(SprintHygieneReader(repo_path).signals(base)) if base is not None else ()
    except RepositoryError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    snapshot = SprintSnapshot(sprint=sprint, specs=spec_metrics, hygiene=hygiene)
    series = snap_store.record(snapshot, as_of)

    if json_out:
        _emit_metrics_json(snapshot, series)
    else:
        _render_metrics(snapshot, series)


def _sprint_specs(specs_dir: Path, sprint: str) -> list[tuple[str, str]]:
    """(spec_id, path-relative-to-cwd) for every spec whose frontmatter is this sprint."""
    selected: list[tuple[str, str]] = []
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        try:
            parsed = parse_spec(path.read_text(encoding="utf-8"))
        except SpecParseError:
            continue
        if parsed.frontmatter.sprint == sprint:
            selected.append((parsed.spec_id, str(path)))
    return selected


def _spec_metrics(
    spec_id, relpath, repo, run_store, turnover, commits, as_of, baseline_30, baseline_90
) -> SpecMetrics:
    transitions = StatusHistoryReader(repo, _repo_relpath(repo, relpath)).transitions(spec_id)
    events = run_store.events_for(spec_id)
    turnover_30 = turnover.turnover(spec_id, window_days=30, as_of=as_of)
    turnover_90 = turnover.turnover(spec_id, window_days=90, as_of=as_of)
    return SpecMetrics(
        spec_id=spec_id,
        cycle_time_seconds=cycle_time_seconds(transitions),
        first_run_pass_rate=first_run_pass_rate(events),
        iterations_to_green=iterations_to_green(events),
        turnover_30d=turnover_30,
        turnover_90d=turnover_90,
        turnover_ratio_30d=turnover_ratio(turnover_30, baseline_30),
        turnover_ratio_90d=turnover_ratio(turnover_90, baseline_90),
        commits=sum(1 for c in commits if spec_id in c.spec_trailers),
    )


def _repo_relpath(repo: Path, relpath: str) -> str:
    """The spec path as git wants it: relative to the repo root, forward slashes."""
    try:
        return Path(relpath).resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return relpath


def _emit_metrics_json(snapshot: SprintSnapshot, series: int) -> None:
    payload = {
        "sprint": snapshot.sprint,
        "series": series,
        "specs": [
            {
                "spec": s.spec_id,
                "cycle_time_seconds": s.cycle_time_seconds,
                "first_run_pass_rate": s.first_run_pass_rate,
                "iterations_to_green": s.iterations_to_green,
                "turnover_30d": s.turnover_30d,
                "turnover_90d": s.turnover_90d,
                "turnover_ratio_30d": s.turnover_ratio_30d,
                "turnover_ratio_90d": s.turnover_ratio_90d,
                "commits": s.commits,
            }
            for s in snapshot.specs
        ],
        "hygiene": [
            {"spec": h.spec_id, "kind": h.kind, "detail": h.detail} for h in snapshot.hygiene
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))


def _render_metrics(snapshot: SprintSnapshot, series: int) -> None:
    table = Table(title=f"Métricas — sprint {snapshot.sprint} (série {series})")
    table.add_column("Spec")
    table.add_column("Cycle time")
    table.add_column("First-run")
    table.add_column("Iter→verde")
    table.add_column("Turnover 30d")
    table.add_column("Commits")
    for s in snapshot.specs:
        table.add_row(
            s.spec_id,
            _fmt_seconds(s.cycle_time_seconds),
            _fmt_pct(s.first_run_pass_rate),
            "—" if s.iterations_to_green is None else str(s.iterations_to_green),
            "—" if s.turnover_30d is None else f"{s.turnover_30d:.2f}",
            str(s.commits),
        )
    console.print(table)
    report = hygiene_report(snapshot.hygiene)
    if report:
        console.print("Higiene (test-tampering):", markup=False, style="yellow")
        for spec_id, signals in report.items():
            for signal in signals:
                console.print(f"  ⚠ {spec_id}: {signal.kind} — {signal.detail}", markup=False)


def _fmt_seconds(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value / 3600:.1f}h"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value * 100:.0f}%"


@app.command()
def survey(
    pr: str = typer.Argument(..., help="ref da PR (ex.: owner/repo#123)"),
    runtime: str = typer.Option(..., "--runtime", help="runtime da implementação"),
    model: str = typer.Option(..., "--model", help="modelo usado (ex.: claude-opus)"),
    spec: str | None = typer.Option(None, "--spec", help="spec; senão derivada do vínculo da PR"),
    aproveitamento: int | None = typer.Option(None, "--aproveitamento", help="1 a 5"),
    retrabalho: str | None = typer.Option(None, "--retrabalho", help="nenhum/leve/pesado"),
    tempo: str | None = typer.Option(None, "--tempo", help="economizou/neutro/custou"),
    comentario: str | None = typer.Option(None, "--comentario", help="comentário livre opcional"),
    skip: bool = typer.Option(False, "--skip", help="pular o survey desta PR"),
    specs_dir: str = typer.Option("specs", "--specs", help="diretório das specs"),
) -> None:
    """Registra a percepção do dev no merge de uma PR (SPEC-014).

    Três itens fechados (aproveitamento 1-5, retrabalho, tempo percebido) e um
    comentário opcional, ancorados à tripla spec × runtime × modelo. O survey é
    skippável e nunca reaparece na mesma PR. A identidade do respondente não é
    guardada — só agregados por sprint/time (ADR-008).
    """
    try:
        gateway = gateway_from_env()
        gateway.migrate()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    store = PerceptionStore(gateway.target)

    if store.has_response(pr):
        console.print(f"• {pr}: já registrado — sem novo prompt (SPEC-014).", markup=False)
        return

    spec_id = spec or _derive_spec_for_pr(gateway.target, pr)
    if spec_id is None:
        err_console.print(
            f"✗ {pr}: sem spec vinculada e sem --spec; nada registrado.",
            markup=False,
            style="red",
        )
        raise typer.Exit(1) from None

    sprint = _sprint_of_spec(Path(specs_dir), spec_id)
    if sprint is None:
        err_console.print(
            f"✗ spec {spec_id} não encontrada em {specs_dir}", markup=False, style="red"
        )
        raise typer.Exit(1) from None

    at = datetime.now(UTC)
    if skip:
        store.record_skip(pr, spec_id, sprint, runtime, model, at)
        console.print(f"• {pr}: survey pulado e registrado (sem penalidade).", markup=False)
        return

    if aproveitamento is None or retrabalho is None or tempo is None:
        err_console.print(
            "✗ informe --aproveitamento, --retrabalho e --tempo (ou --skip).",
            markup=False,
            style="red",
        )
        raise typer.Exit(1) from None
    try:
        validate_answers(aproveitamento, retrabalho, tempo)
    except PerceptionError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    sample = PerceptionSample(
        pr_ref=pr,
        spec_id=spec_id,
        sprint=sprint,
        runtime=runtime,
        model=model,
        aproveitamento=aproveitamento,
        retrabalho=retrabalho,  # type: ignore[arg-type]
        tempo_percebido=tempo,  # type: ignore[arg-type]
        comentario=comentario,
    )
    store.record_sample(sample, at)
    console.print(f"✓ {pr}: percepção registrada para {spec_id} ({runtime}/{model}).", markup=False)


@app.command()
def perception(
    sprint: str = typer.Argument(..., help="sprint a agregar (ex.: 2026-A4)"),
    json_out: bool = typer.Option(False, "--json", help="saída legível por máquina (JSON)"),
) -> None:
    """Agrega a percepção de uma sprint e cruza com o cycle time real (SPEC-014).

    Só agregados: contagens, distribuições e o gap de percepção (proporção de
    amostras cuja direção percebida diverge da medida pelo cycle time da SPEC-013).
    Nenhuma resposta individual é exposta (ADR-008).
    """
    try:
        gateway = gateway_from_env()
        gateway.migrate()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    store = PerceptionStore(gateway.target)
    snapshot = MetricSnapshotStore(gateway.target).latest(sprint)
    cycle_times = (
        {
            s.spec_id: s.cycle_time_seconds
            for s in snapshot.specs
            if s.cycle_time_seconds is not None
        }
        if snapshot is not None
        else {}
    )
    agg = aggregate_perception(
        sprint,
        store.samples_for_sprint(sprint),
        store.skips_for_sprint(sprint),
        cycle_times,
    )
    if json_out:
        _emit_perception_json(agg)
    else:
        _render_perception(agg)


def _derive_spec_for_pr(target, pr: str) -> str | None:
    """The single spec linked to a PR via its commits (SPEC-009); None if 0 or >1."""
    if "#" not in pr:
        return None
    repo, _, number = pr.rpartition("#")
    if not number.isdigit():
        return None
    spec_ids = RepositoryStore(target).spec_ids_for_pr(repo, int(number))
    return next(iter(spec_ids)) if len(spec_ids) == 1 else None


def _sprint_of_spec(specs_dir: Path, spec_id: str) -> str | None:
    for path in specs_dir.glob(f"{spec_id}*.md"):
        try:
            return parse_spec(path.read_text(encoding="utf-8")).frontmatter.sprint
        except SpecParseError:
            return None
    return None


def _emit_perception_json(agg) -> None:
    payload = {
        "sprint": agg.sprint,
        "n_samples": agg.n_samples,
        "n_skipped": agg.n_skipped,
        "aproveitamento_mean": agg.aproveitamento_mean,
        "retrabalho_dist": dict(agg.retrabalho_dist),
        "tempo_dist": dict(agg.tempo_dist),
        "perception_gap": agg.perception_gap,
    }
    print(json.dumps(payload, ensure_ascii=False))


def _render_perception(agg) -> None:
    table = Table(title=f"Percepção — sprint {agg.sprint}")
    table.add_column("Métrica")
    table.add_column("Valor")
    table.add_row("Amostras", str(agg.n_samples))
    table.add_row("Skips", str(agg.n_skipped))
    table.add_row("Aproveitamento médio", _fmt_mean(agg.aproveitamento_mean))
    table.add_row("Tempo percebido", _fmt_dist(agg.tempo_dist))
    table.add_row("Retrabalho", _fmt_dist(agg.retrabalho_dist))
    table.add_row(
        "Gap de percepção",
        "—" if agg.perception_gap is None else f"{agg.perception_gap * 100:.0f}%",
    )
    console.print(table)
    if agg.perception_gap is None:
        console.print(
            "Gap indisponível: compute as métricas da sprint (specharness metrics) primeiro.",
            markup=False,
            style="yellow",
        )


def _fmt_mean(value: float | None) -> str:
    return "—" if value is None else f"{value:.1f}"


def _fmt_dist(dist) -> str:
    return " · ".join(f"{k}:{v}" for k, v in dist.items())


@connect_app.command("db")
def connect_db() -> None:
    """Conecta ao banco, criando e migrando o que faltar.

    Sem configuração, cria um SQLite local em .specharness/ e o migra — zero
    perguntas (ADR-002). Defina SPECHARNESS_DATABASE_URL para usar o seu
    Postgres; nada mais muda.
    """
    try:
        gateway = gateway_from_env()
        gateway.healthcheck()
        result = gateway.migrate()
    except DatabaseError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    console.print(f"✓ Conectado — {_describe(gateway)}", markup=False, soft_wrap=True)
    if result.was_noop:
        console.print(f"  Migrações em dia (revisão {result.revision}).", markup=False)
    else:
        applied = ", ".join(result.applied)
        console.print(
            f"  Migrações aplicadas: {applied} (revisão {result.revision}).", markup=False
        )


def _describe(gateway) -> str:
    """Where we landed, in terms the user can act on — never with a password."""
    target = gateway.target
    if target.sqlite_path is None:
        return f"PostgreSQL em {target.safe_sync_url}"
    path = Path(target.sqlite_path)
    try:
        # A relative path is what the user recognises as "o banco deste repo".
        shown = path.relative_to(Path.cwd()).as_posix()
    except ValueError:
        shown = path.as_posix()
    return f"SQLite em {shown}"


@connect_app.command("repo")
def connect_repo() -> None:
    """Ingere commits (com trailers) e pull requests do repositório GitHub (SPEC-006).

    Lê o histórico do git local (ADR-011) e complementa com os PRs da API do
    GitHub. Precisa de GITHUB_TOKEN com escopo mínimo de leitura de Contents e
    Pull requests. O reprocessamento é idempotente: rodar de novo sem novidades
    não cria registros.
    """
    reader = LocalGitCommitReader(Path.cwd())
    try:
        ref = reader.remote_ref()
    except RepositoryError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    if not os.environ.get(GITHUB_TOKEN_ENV, "").strip():
        exc = AuthenticationFailed.for_repo(ref.slug, detail=f"{GITHUB_TOKEN_ENV} não definida")
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    token = os.environ[GITHUB_TOKEN_ENV].strip()

    try:
        commits = list(reader.commits())
        pull_requests = list(GitHubClient(ref, token).pull_requests())
        gateway = gateway_from_env()
        gateway.migrate()
        result = RepositoryStore(gateway.target).sync(ref.slug, commits, pull_requests)
    except (RepositoryError, DatabaseError) as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    console.print(f"✓ Repositório conectado — {ref.slug}", markup=False, soft_wrap=True)
    console.print(
        f"  {result.total_commits} commits ({result.new_commits} novos) · "
        f"{result.total_pull_requests} PRs ({result.new_pull_requests} novos).",
        markup=False,
    )
    if result.was_noop:
        console.print("  Nada novo desde o último sync.", markup=False)


@connect_app.command("tracker")
def connect_tracker() -> None:
    """Importa issues e versions do Redmine como WorkItems canônicos (SPEC-007).

    Lê a URL e o projeto de `specharness.yaml` (seção `tracker`) e a API key de
    REDMINE_API_KEY. O import é idempotente: rodar de novo atualiza mudanças de
    status e não duplica nada.
    """
    try:
        config = _load_tracker()
    except ConfigError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    if config is None or not config.url or not config.project:
        exc = InvalidTrackerConfig.because(
            f"defina tracker.url e tracker.project em {CONFIG_FILENAME}"
        )
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    if not os.environ.get(REDMINE_API_KEY_ENV, "").strip():
        exc = TrackerAuthenticationFailed.for_tracker(
            config.url, detail=f"{REDMINE_API_KEY_ENV} não definida"
        )
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    api_key = os.environ[REDMINE_API_KEY_ENV].strip()

    try:
        client = RedmineClient(config.url, api_key, config.project)
        items = list(client.work_items())
        gateway = gateway_from_env()
        gateway.migrate()
        result = WorkItemStore(gateway.target).sync(client.origin, items)
    except (TrackerError, DatabaseError) as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    console.print(f"✓ Tracker conectado — Redmine · {config.project}", markup=False, soft_wrap=True)
    console.print(
        f"  {result.total_items} WorkItems "
        f"({result.new_items} novos, {result.updated_items} atualizados).",
        markup=False,
    )
    if result.was_noop:
        console.print("  Nada novo desde o último import.", markup=False)


@connect_app.command("issues")
def connect_issues() -> None:
    """Importa issues do GitHub como WorkItems canônicos (SPEC-008).

    Reusa a conexão da SPEC-006: o repositório vem do remote do git local e a
    credencial de GITHUB_TOKEN. O import é idempotente e captura fechamentos:
    uma issue fechada no GitHub vira estado `closed` no próximo sync.
    """
    reader = LocalGitCommitReader(Path.cwd())
    try:
        ref = reader.remote_ref()
    except RepositoryError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    if not os.environ.get(GITHUB_TOKEN_ENV, "").strip():
        exc = TrackerAuthenticationFailed.for_tracker(
            ref.slug, detail=f"{GITHUB_TOKEN_ENV} não definida", key_env=GITHUB_TOKEN_ENV
        )
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None
    token = os.environ[GITHUB_TOKEN_ENV].strip()

    try:
        items = list(GitHubIssuesClient(ref, token).work_items())
        gateway = gateway_from_env()
        gateway.migrate()
        result = WorkItemStore(gateway.target).sync("github", items)
    except (TrackerError, DatabaseError) as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    console.print(f"✓ Issues importadas — {ref.slug}", markup=False, soft_wrap=True)
    console.print(
        f"  {result.total_items} WorkItems "
        f"({result.new_items} novos, {result.updated_items} atualizados).",
        markup=False,
    )
    if result.was_noop:
        console.print("  Nada novo desde o último import.", markup=False)


@llm_app.command("test")
def llm_test(
    task: str | None = typer.Option(
        None, "--task", help="Usa o modelo roteado para esta tarefa em specharness.yaml."
    ),
) -> None:
    """Valida a conexão LLM com uma chamada real e structured output (SPEC-005).

    Detecta o provedor pelo ambiente: uma API key (ANTHROPIC/OPENAI/AZURE) ou o
    Ollama local, oferecido como caminho de custo zero. Sem nenhuma via
    funcional, o Readiness Gate fica bloqueado — as funções determinísticas
    seguem disponíveis (ADR-006). O roteamento por tarefa lê specharness.yaml.
    """
    env = os.environ
    try:
        routing = _load_routing()
    except ConfigError as exc:
        err_console.print(f"✗ {CONFIG_FILENAME}: {exc}", markup=False, style="red")
        raise typer.Exit(1) from None

    # No task pinned: detect what is actually usable. No path at all blocks the
    # gate with guidance for both vias, but never the deterministic floor.
    if task is None and not detect_providers(env):
        status = onboarding_status(semantic_ready=False)
        err_console.print(f"✗ {status.guidance}", markup=False, style="red")
        err_console.print("  Funções determinísticas seguem disponíveis (ADR-006).", markup=False)
        raise typer.Exit(1) from None

    try:
        report = check_connection(env, routing=routing, task=task)
    except LLMError as exc:
        err_console.print(f"✗ {exc}", markup=False, style="red")
        err_console.print(
            "  Camada semântica pendente; funções determinísticas seguem (ADR-006).",
            markup=False,
        )
        raise typer.Exit(1) from None

    console.print(
        f"✓ LLM conectado — {report.provider} · {report.model}", markup=False, soft_wrap=True
    )
    console.print(
        f"  Latência {report.latency_s:.2f}s · custo estimado {report.cost_label}", markup=False
    )


def _load_routing() -> RoutingConfig | None:
    """Read specharness.yaml from the repo root, if present."""
    path = Path.cwd() / CONFIG_FILENAME
    if not path.is_file():
        return None
    return load_routing(path.read_text(encoding="utf-8"))


def _load_tracker() -> TrackerConfig | None:
    """Read the tracker section of specharness.yaml from the repo root, if present."""
    path = Path.cwd() / CONFIG_FILENAME
    if not path.is_file():
        return None
    return load_tracker(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    app()
