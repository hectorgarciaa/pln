"""Construcción de chunks sustanciales con solapamiento configurable."""

from __future__ import annotations

from p4.app.errors import ConfigurationError
from p4.app.models import Chunk, Document
from p4.app.preprocessing import SpanishTextPreprocessor
from p4.app.utils import count_words


def build_chunks(
    documents: list[Document],
    preprocessor: SpanishTextPreprocessor,
    target_words: int,
    overlap_words: int,
) -> list[Chunk]:
    """Genera chunks coherentes a partir de párrafos contiguos."""

    if target_words <= 0:
        raise ConfigurationError("chunk_target_words debe ser mayor que cero")
    if overlap_words < 0:
        raise ConfigurationError("chunk_overlap_words no puede ser negativo")
    if overlap_words >= target_words:
        raise ConfigurationError(
            "chunk_overlap_words debe ser menor que chunk_target_words"
        )

    raw_chunks: list[dict[str, object]] = []
    for document in documents:
        raw_chunks.extend(
            _build_document_chunks(
                document, target_words=target_words, overlap_words=overlap_words
            )
        )

    analyses = preprocessor.analyze_many([chunk["search_text"] for chunk in raw_chunks])
    chunks: list[Chunk] = []
    for raw_chunk, analysis in zip(raw_chunks, analyses):
        chunks.append(
            Chunk(
                chunk_id=str(raw_chunk["chunk_id"]),
                document_id=str(raw_chunk["document_id"]),
                part=str(raw_chunk["part"]),
                title=str(raw_chunk["title"]),
                paragraph_ids=list(raw_chunk["paragraph_ids"]),
                start_paragraph=int(raw_chunk["start_paragraph"]),
                end_paragraph=int(raw_chunk["end_paragraph"]),
                text=str(raw_chunk["text"]),
                search_text=str(raw_chunk["search_text"]),
                word_count=int(raw_chunk["word_count"]),
                surface_tokens=analysis.surface_tokens,
                lemma_tokens=analysis.lemma_tokens,
                normalized_text=analysis.normalized_text,
                metadata=dict(raw_chunk["metadata"]),
            )
        )
    return chunks


def _build_document_chunks(
    document: Document, target_words: int, overlap_words: int
) -> list[dict[str, object]]:
    paragraphs = document.paragraphs
    chunks: list[dict[str, object]] = []

    start = 0
    chunk_index = 0
    while start < len(paragraphs):
        end = start
        accumulated_words = 0

        while end < len(paragraphs) and (
            accumulated_words < target_words or end == start
        ):
            accumulated_words += paragraphs[end].word_count
            end += 1

        selected = paragraphs[start:end]
        text = " ".join(paragraph.text for paragraph in selected)
        paragraph_ids = [paragraph.paragraph_id for paragraph in selected]
        chunks.append(
            {
                "chunk_id": f"{document.document_id}::chunk{chunk_index:03d}",
                "document_id": document.document_id,
                "part": document.part,
                "title": document.title,
                "paragraph_ids": paragraph_ids,
                "start_paragraph": selected[0].order,
                "end_paragraph": selected[-1].order,
                "text": text,
                "search_text": f"{document.title}. {text}",
                "word_count": count_words(text),
                "metadata": {
                    "document_title": document.title,
                    "document_word_count": document.metadata.get("word_count", 0),
                    "paragraph_count": len(selected),
                },
            }
        )
        chunk_index += 1

        if end >= len(paragraphs):
            break

        retained_words = 0
        next_start = end
        for candidate in range(end - 1, start, -1):
            retained_words += paragraphs[candidate].word_count
            next_start = candidate
            if retained_words >= overlap_words:
                break

        if next_start <= start:
            next_start = start + 1
        start = next_start

    return chunks
