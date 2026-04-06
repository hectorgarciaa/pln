"""Persistencia de chunks, índices y embeddings."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from p4.app.errors import ArtifactMissingError
from p4.app.models import Chunk, Document


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Guarda un JSON UTF-8 con formato legible."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    """Lee un JSON desde disco."""

    ensure_artifact(path)
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_artifact(path: Path) -> None:
    """Comprueba que un artefacto exista en disco."""

    if not path.exists():
        raise ArtifactMissingError(
            f"No existe el artefacto requerido: {path}. Ejecuta primero el comando de construcción correspondiente."
        )


def save_chunks(path: Path, chunks: list[Chunk], manifest: dict[str, Any]) -> None:
    """Persiste el listado de chunks y su manifiesto."""

    write_json(
        path, {"manifest": manifest, "chunks": [chunk.to_dict() for chunk in chunks]}
    )


def load_chunks(path: Path) -> tuple[dict[str, Any], list[Chunk]]:
    """Carga el listado de chunks persistidos."""

    payload = read_json(path)
    return payload["manifest"], [Chunk.from_dict(item) for item in payload["chunks"]]


def save_documents(
    path: Path, documents: list[Document], manifest: dict[str, Any]
) -> None:
    """Permite persistir documentos completos si se necesita depuración adicional."""

    write_json(
        path,
        {
            "manifest": manifest,
            "documents": [document.to_dict() for document in documents],
        },
    )


def save_classical_index(path: Path, payload: dict[str, Any]) -> None:
    """Guarda el índice clásico serializado."""

    write_json(path, payload)


def load_classical_index(path: Path) -> dict[str, Any]:
    """Carga el índice clásico serializado."""

    return read_json(path)


def save_semantic_embeddings(path: Path, embeddings: np.ndarray) -> None:
    """Guarda la matriz de embeddings en formato comprimido."""

    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, embeddings=embeddings.astype(np.float32))


def load_semantic_embeddings(path: Path) -> np.ndarray:
    """Carga la matriz de embeddings desde disco."""

    ensure_artifact(path)
    with np.load(path) as payload:
        return payload["embeddings"].astype(np.float32)
