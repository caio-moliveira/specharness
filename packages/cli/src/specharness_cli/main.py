"""specharness CLI (SPEC-002 §1.2). Commands land as their specs are built."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from specharness_adapters.db import RepositoryStore, WorkItemStore, gateway_from_env
from specharness_adapters.git import LocalGitCommitReader
from specharness_adapters.github import GitHubClient
from specharness_adapters.github_issues import GitHubIssuesClient
from specharness_adapters.llm import check_connection, detect_providers
from specharness_adapters.redmine import RedmineClient
from specharness_core import (
    SpecInfo,
    SpecParseError,
    __version__,
    link_commits,
    parse_spec,
)
from specharness_core.config import (
    CONFIG_FILENAME,
    ConfigError,
    RoutingConfig,
    TrackerConfig,
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
        ("specharness ready <spec>", "SPEC-010/011", "planejado"),
        ("specharness verify", "SPEC-012", "planejado"),
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
