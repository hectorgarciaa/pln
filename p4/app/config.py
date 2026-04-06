"""Carga tipada de configuración con Dynaconf y variables de entorno."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from dynaconf import Dynaconf

from p4.conf import FRONTMATTER_IDS, STOPWORDS_ES


@dataclass(frozen=True, slots=True)
class AppSettings:
    """Configuración efectiva de la aplicación."""

    repo_root: Path
    project_dir: Path
    corpus_path: Path
    artifacts_dir: Path
    logs_dir: Path
    chunks_path: Path
    classical_index_path: Path
    semantic_embeddings_path: Path
    semantic_manifest_path: Path
    spacy_model: str
    top_k: int
    chunk_target_words: int
    chunk_overlap_words: int
    surface_weight: float
    lemma_weight: float
    semantic_batch_size: int
    rag_enabled: bool


@lru_cache(maxsize=1)
def load_settings() -> AppSettings:
    """Carga la configuración desde `settings.toml` y `.env`."""

    project_dir = Path(__file__).resolve().parents[1]
    repo_root = project_dir.parent
    load_dotenv(project_dir / ".env", override=False)

    dynasettings = Dynaconf(
        envvar_prefix="QUIJOTE",
        settings_files=[project_dir / "settings.toml"],
        load_dotenv=False,
    )

    artifacts_dir = project_dir / dynasettings.paths.artifacts_dir
    logs_dir = project_dir / dynasettings.paths.logs_dir
    ensure_runtime_directories(artifacts_dir, logs_dir)

    return AppSettings(
        repo_root=repo_root,
        project_dir=project_dir,
        corpus_path=project_dir / dynasettings.paths.corpus_path,
        artifacts_dir=artifacts_dir,
        logs_dir=logs_dir,
        chunks_path=artifacts_dir / dynasettings.paths.chunks_filename,
        classical_index_path=artifacts_dir
        / dynasettings.paths.classical_index_filename,
        semantic_embeddings_path=artifacts_dir
        / dynasettings.paths.semantic_embeddings_filename,
        semantic_manifest_path=artifacts_dir
        / dynasettings.paths.semantic_manifest_filename,
        spacy_model=str(dynasettings.preprocessing.spacy_model),
        top_k=int(dynasettings.search.top_k),
        chunk_target_words=int(dynasettings.chunking.target_words),
        chunk_overlap_words=int(dynasettings.chunking.overlap_words),
        surface_weight=float(dynasettings.search.surface_weight),
        lemma_weight=float(dynasettings.search.lemma_weight),
        semantic_batch_size=int(dynasettings.semantic.batch_size),
        rag_enabled=bool(dynasettings.rag.enabled),
    )


def ensure_runtime_directories(*paths: Path) -> None:
    """Crea directorios de trabajo si no existen."""

    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def frontmatter_ids() -> set[str]:
    """Devuelve una copia de los IDs descartados al extraer capítulos."""

    return set(FRONTMATTER_IDS)


def custom_stopwords() -> set[str]:
    """Devuelve las stopwords manuales en formato normalizado."""

    return set(STOPWORDS_ES)
