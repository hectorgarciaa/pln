"""Búsqueda semántica con vectores de spaCy `es_core_news_lg`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from p4.app.errors import SemanticModelError
from p4.app.models import Chunk, Document, SearchResult
from p4.app.utils import extract_fragment


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


class SpacyVectorEmbedder:
    """Genera embeddings semánticos con el vector de documento de spaCy."""

    REQUIRED_MODEL = "es_core_news_lg"

    def __init__(self, nlp, model_name: str, batch_size: int = 32) -> None:
        self.model = model_name
        self._nlp = nlp
        self.batch_size = batch_size
        if model_name != self.REQUIRED_MODEL:
            raise SemanticModelError(
                "La búsqueda semántica de esta práctica debe usar spaCy con el modelo "
                f"{self.REQUIRED_MODEL!r}. Ajusta `spacy_model` y reconstruye los embeddings."
            )
        if getattr(self._nlp.vocab, "vectors_length", 0) <= 0:
            raise SemanticModelError(
                "El modelo de spaCy cargado no incluye vectores semánticos. "
                f"Instala y usa {self.REQUIRED_MODEL!r}."
            )

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Genera embeddings para una lista de textos."""

        clean_texts = [text.strip() for text in texts if text and text.strip()]
        if not clean_texts:
            return np.zeros((0, 0), dtype=np.float32)

        vectors: list[np.ndarray] = []
        for doc in self._nlp.pipe(clean_texts, batch_size=self.batch_size):
            vector = np.asarray(doc.vector, dtype=np.float32)
            if vector.size == 0:
                raise SemanticModelError(
                    "spaCy no devolvió vectores de documento válidos. "
                    f"Comprueba que {self.REQUIRED_MODEL!r} está instalado correctamente."
                )
            vectors.append(vector)

        embeddings = np.vstack(vectors).astype(np.float32)
        if embeddings.ndim != 2:
            raise SemanticModelError(
                "spaCy devolvió embeddings con un formato inesperado."
            )
        return embeddings


@dataclass(slots=True)
class SemanticSearchEngine:
    """Motor de similitud coseno sobre embeddings persistidos."""

    chunk_ids: list[str]
    embeddings: np.ndarray
    model: str

    @classmethod
    def build(
        cls,
        chunks: list[Chunk],
        documents: list[Document],
        embedder: SpacyVectorEmbedder,
    ) -> "SemanticSearchEngine":
        paragraph_texts: list[str] = []
        paragraph_ids: list[str] = []
        for document in documents:
            for paragraph in document.paragraphs:
                paragraph_ids.append(paragraph.paragraph_id)
                paragraph_texts.append(paragraph.text)

        paragraph_embeddings = embedder.embed_texts(paragraph_texts)
        paragraph_lookup = {
            paragraph_id: paragraph_embeddings[index]
            for index, paragraph_id in enumerate(paragraph_ids)
        }

        chunk_vectors: list[np.ndarray] = []
        for chunk in chunks:
            vectors = [
                paragraph_lookup[paragraph_id]
                for paragraph_id in chunk.paragraph_ids
                if paragraph_id in paragraph_lookup
            ]
            if not vectors:
                raise SemanticModelError(
                    f"No se pudieron agregar embeddings para el chunk {chunk.chunk_id}: faltan párrafos de origen."
                )
            chunk_vectors.append(np.mean(np.vstack(vectors), axis=0))

        embeddings = _normalize_rows(np.vstack(chunk_vectors).astype(np.float32))
        return cls(
            chunk_ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            model=embedder.model,
        )

    def to_manifest(self) -> dict[str, Any]:
        return {
            "chunk_ids": self.chunk_ids,
            "model": self.model,
            "dimensions": int(self.embeddings.shape[1]) if self.embeddings.size else 0,
        }

    @classmethod
    def from_manifest(
        cls, manifest: dict[str, Any], embeddings: np.ndarray
    ) -> "SemanticSearchEngine":
        return cls(
            chunk_ids=list(manifest["chunk_ids"]),
            embeddings=_normalize_rows(embeddings.astype(np.float32)),
            model=str(manifest["model"]),
        )

    def search(
        self,
        query: str,
        chunks: list[Chunk],
        embedder: SpacyVectorEmbedder,
        top_k: int,
    ) -> list[SearchResult]:
        """Ejecuta una búsqueda semántica por similitud coseno."""

        query_embedding = embedder.embed_texts([query])
        if query_embedding.size == 0:
            return []

        query_vector = _normalize_rows(query_embedding)[0]
        scores = self.embeddings @ query_vector
        ranked_indices = np.argsort(scores)[::-1]

        results: list[SearchResult] = []
        for document_index in ranked_indices:
            score = float(scores[document_index])
            if score <= 0:
                continue
            chunk = chunks[int(document_index)]
            results.append(
                SearchResult(
                    rank=len(results) + 1,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    part=chunk.part,
                    title=chunk.title,
                    score=round(score, 6),
                    fragment=extract_fragment(
                        chunk.text, [query, *chunk.lemma_tokens[:10]]
                    ),
                    text=chunk.text,
                    metadata={
                        "chunk_word_count": chunk.word_count,
                        "paragraph_span": f"{chunk.start_paragraph}-{chunk.end_paragraph}",
                        "paragraph_count": chunk.metadata.get("paragraph_count"),
                    },
                    explanation={
                        "mode": "semantic",
                        "embedding_model": self.model,
                        "vector_backend": "spaCy document vectors",
                        "query": query,
                    },
                )
            )
            if len(results) >= top_k:
                break
        return results
