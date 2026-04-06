"""Entrada de ejecución para la CLI/TUI."""

from p4.app.cli import app


def main() -> int:
    """Ejecuta la CLI de Typer."""

    app()
    return 0
