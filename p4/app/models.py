"""Modelos de datos del proyecto."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Paragraph:
    """Unidad textual básica extraída del documento fuente."""

    paragraph_id: str
    document_id: str
    order: int
    text: str
    word_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paragraph":
        return cls(**data)


@dataclass(slots=True)
class Document:
    """Representa un capítulo del corpus."""

    document_id: str
    part: str
    title: str
    paragraphs: list[Paragraph]
    source_path: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["paragraphs"] = [paragraph.to_dict() for paragraph in self.paragraphs]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Document":
        payload = dict(data)
        payload["paragraphs"] = [
            Paragraph.from_dict(item) for item in payload["paragraphs"]
        ]
        return cls(**payload)


@dataclass(slots=True)
class TextAnalysis:
    """Resultado del pipeline de normalización lingüística."""

    original_text: str
    cleaned_text: str
    surface_tokens: list[str]
    lemma_tokens: list[str]

    @property
    def normalized_text(self) -> str:
        return " ".join(self.lemma_tokens)


@dataclass(slots=True)
class Chunk:
    """Fragmento recuperable del corpus."""

    chunk_id: str
    document_id: str
    part: str
    title: str
    paragraph_ids: list[str]
    start_paragraph: int
    end_paragraph: int
    text: str
    search_text: str
    word_count: int
    surface_tokens: list[str]
    lemma_tokens: list[str]
    normalized_text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chunk":
        return cls(**data)


@dataclass(slots=True)
class SearchResult:
    """Resultado de una búsqueda clásica o semántica."""

    rank: int
    chunk_id: str
    document_id: str
    part: str
    title: str
    score: float
    fragment: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RagSource:
    """Fuente recuperada para construir y justificar una respuesta RAG."""

    rank: int
    source_id: str
    chunk_id: str
    document_id: str
    part: str
    title: str
    score: float
    fragment: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    explanation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RagResponse:
    """Respuesta final generada por el flujo RAG con sus fuentes."""

    query: str
    answer: str
    sources: list[RagSource]
    references: list[str]
    model: str
    context: str
    raw_response: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sources"] = [source.to_dict() for source in self.sources]
        return payload
