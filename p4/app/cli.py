"""CLI secundaria para construir recursos y lanzar la TUI."""

from __future__ import annotations

from enum import Enum

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from p4.app.errors import QuijoteIRError
from p4.app.models import RagResponse
from p4.app.services import QuijoteSearchService


console = Console()
app = typer.Typer(
    add_completion=False,
    no_args_is_help=False,
    help="Herramienta de recuperación de información sobre el Quijote.",
)


class SearchMode(str, Enum):
    classical = "classical"
    semantic = "semantic"
    rag = "rag"


def _service() -> QuijoteSearchService:
    return QuijoteSearchService()


def _render_results(mode: str, query: str, results) -> None:
    table = Table(title=f'Resultados para "{query}" ({mode})', show_lines=True)
    table.add_column("#", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Parte")
    table.add_column("Capítulo")
    table.add_column("Fragmento", overflow="fold")

    for result in results:
        table.add_row(
            str(result.rank),
            f"{result.score:.6f}",
            result.part,
            result.title,
            result.fragment,
        )
    console.print(table)


def _render_rag_response(response: RagResponse) -> None:
    answer_title = (
        "Respuesta RAG (evidencia insuficiente)"
        if response.metadata.get("insufficient_evidence")
        else "Respuesta RAG"
    )
    console.print(
        Panel(
            response.answer,
            title=answer_title,
            border_style="green",
        )
    )

    table = Table(title=f'Fuentes para "{response.query}"', show_lines=True)
    table.add_column("Ref")
    table.add_column("Usada")
    table.add_column("Score", justify="right")
    table.add_column("Parte")
    table.add_column("Capítulo")
    table.add_column("Chunk")
    table.add_column("Fragmento", overflow="fold")

    used_references = set(response.references)
    for source in response.sources:
        table.add_row(
            source.source_id or "-",
            "sí" if source.source_id in used_references else "no",
            f"{source.score:.6f}",
            source.part,
            source.title,
            source.chunk_id,
            source.fragment,
        )
    console.print(table)


def _run_or_die(action) -> None:
    try:
        action()
    except QuijoteIRError as exc:
        console.print(Panel(str(exc), title="Error", border_style="red"))
        raise typer.Exit(code=1) from exc


@app.callback(invoke_without_command=True)
def default(ctx: typer.Context) -> None:
    """Lanza la TUI si no se especifica ningún subcomando."""

    if ctx.invoked_subcommand is None:
        tui()


@app.command("status")
def status() -> None:
    """Muestra el estado de los artefactos persistidos."""

    def _action() -> None:
        service = _service()
        summary = service.describe_artifacts()
        table = Table(title="Estado de artefactos")
        table.add_column("Recurso")
        table.add_column("Existe")
        table.add_column("Ruta")
        table.add_column("Resumen")
        for name, info in summary.items():
            manifest = info.get("manifest", {})
            resume = (
                ", ".join(f"{key}={value}" for key, value in manifest.items())
                if manifest
                else "-"
            )
            table.add_row(name, "sí" if info["exists"] else "no", info["path"], resume)
        console.print(table)

    _run_or_die(_action)


@app.command("build-chunks")
def build_chunks() -> None:
    """Regenera los chunks y su manifiesto."""

    def _action() -> None:
        manifest, _ = _service().build_chunks()
        console.print(
            Panel.fit(
                f"Chunks regenerados: {manifest['total_chunks']}",
                title="OK",
                border_style="green",
            )
        )

    _run_or_die(_action)


@app.command("build-classical")
def build_classical() -> None:
    """Regenera el índice clásico."""

    def _action() -> None:
        manifest = _service().build_classical_index()
        console.print(
            Panel.fit(
                f"Índice clásico regenerado para {manifest['document_count']} chunks.",
                title="OK",
                border_style="green",
            )
        )

    _run_or_die(_action)


@app.command("build-semantic")
def build_semantic() -> None:
    """Regenera los embeddings y el índice semántico."""

    def _action() -> None:
        manifest = _service().build_semantic_index()
        console.print(
            Panel.fit(
                f"Embeddings regenerados con {manifest['model']} ({manifest['dimensions']} dimensiones).",
                title="OK",
                border_style="green",
            )
        )

    _run_or_die(_action)


@app.command("build-all")
def build_all(
    no_semantic: bool = typer.Option(
        False,
        "--no-semantic",
        help="Construye solo chunks e índice clásico.",
    ),
) -> None:
    """Reconstruye todos los recursos principales."""

    def _action() -> None:
        manifests = _service().build_all(include_semantic=not no_semantic)
        lines = [
            f"Chunks: {manifests['chunks']['total_chunks']}",
            f"Índice clásico: {manifests['classical']['document_count']} chunks",
        ]
        if manifests["semantic"] is not None:
            lines.append(
                f"Embeddings: {manifests['semantic']['model']} ({manifests['semantic']['dimensions']} dims)"
            )
        console.print(
            Panel("\n".join(lines), title="Build completado", border_style="green")
        )

    _run_or_die(_action)


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Consulta de texto libre."),
    mode: SearchMode = typer.Option(
        SearchMode.classical, "--mode", "-m", case_sensitive=False
    ),
    top_k: int = typer.Option(
        5, "--top-k", "-k", min=1, help="Número de resultados a mostrar."
    ),
) -> None:
    """Ejecuta una búsqueda y muestra resultados en consola."""

    def _action() -> None:
        service = _service()
        if mode is SearchMode.rag:
            _render_rag_response(service.answer_rag(query, max_sources=top_k))
            return

        results = service.search(mode.value, query, top_k=top_k)
        if not results:
            console.print(
                Panel(
                    "No se encontraron resultados.",
                    title="Sin resultados",
                    border_style="yellow",
                )
            )
            return
        _render_results(mode.value, query, results)

    _run_or_die(_action)


@app.command("rag")
def rag(
    query: str = typer.Argument(..., help="Consulta de texto libre."),
    max_sources: int = typer.Option(
        4, "--max-sources", "-k", min=1, help="Número máximo de fuentes a mostrar."
    ),
) -> None:
    """Ejecuta el modo RAG y muestra respuesta más fuentes citadas."""

    def _action() -> None:
        response = _service().answer_rag(query, max_sources=max_sources)
        _render_rag_response(response)

    _run_or_die(_action)


@app.command("tui")
def tui() -> None:
    """Lanza la interfaz principal interactiva en terminal."""

    def _action() -> None:
        from p4.app.tui.app import QuijoteSearchTUI

        QuijoteSearchTUI(service=_service()).run()

    _run_or_die(_action)
