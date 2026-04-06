"""Punto de extensión para RAG, desactivado por defecto."""

from __future__ import annotations

from p4.app.errors import ConfigurationError


def ensure_rag_disabled(enabled: bool) -> None:
    """Protege el flujo principal mientras RAG siga fuera del alcance obligatorio."""

    if enabled:
        raise ConfigurationError(
            "RAG está preparado solo como extensión futura y permanece desactivado por defecto en esta entrega."
        )
