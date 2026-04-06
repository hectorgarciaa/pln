"""Búsqueda clásica con índices TF-IDF implementados con `numpy`."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log, sqrt
from typing import Any

import numpy as np

from p4.app.models import Chunk, SearchResult, TextAnalysis
from p4.app.utils import extract_fragment


@dataclass(slots=True)
class InvertedTfidfIndex:
    """Índice invertido con pesos TF-IDF y normalización coseno."""

    name: str
    document_count: int
    idf: dict[str, float]
    postings: dict[str, list[tuple[int, float]]]
    doc_norms: np.ndarray

    @classmethod
    def build(cls, name: str, token_lists: list[list[str]]) -> "InvertedTfidfIndex":
        document_count = len(token_lists)
        term_frequencies = [Counter(tokens) for tokens in token_lists]
        document_frequencies: Counter[str] = Counter()
        for frequencies in term_frequencies:
            document_frequencies.update(frequencies.keys())

        idf = {
            term: float(log((1 + document_count) / (1 + frequency)) + 1.0)
            for term, frequency in document_frequencies.items()
        }

        postings: dict[str, list[tuple[int, float]]] = defaultdict(list)
        doc_norms = np.zeros(document_count, dtype=np.float32)
        for document_index, frequencies in enumerate(term_frequencies):
            for term, term_frequency in frequencies.items():
                weight = float((1.0 + log(term_frequency)) * idf[term])
                postings[term].append((document_index, weight))
                doc_norms[document_index] += weight * weight

        doc_norms = np.sqrt(doc_norms).astype(np.float32)
        return cls(
            name=name,
            document_count=document_count,
            idf=idf,
            postings=dict(postings),
            doc_norms=doc_norms,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvertedTfidfIndex":
        return cls(
            name=payload["name"],
            document_count=int(payload["document_count"]),
            idf={term: float(value) for term, value in payload["idf"].items()},
            postings={
                term: [
                    (int(document_id), float(weight)) for document_id, weight in values
                ]
                for term, values in payload["postings"].items()
            },
            doc_norms=np.asarray(payload["doc_norms"], dtype=np.float32),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "document_count": self.document_count,
            "idf": self.idf,
            "postings": self.postings,
            "doc_norms": self.doc_norms.tolist(),
        }

    def score(self, terms: list[str]) -> tuple[np.ndarray, dict[int, list[str]]]:
        """Calcula similitud coseno TF-IDF para una consulta tokenizada."""

        scores = np.zeros(self.document_count, dtype=np.float32)
        if not terms:
            return scores, {}

        query_frequencies = Counter(terms)
        matches: dict[int, set[str]] = defaultdict(set)
        query_norm_sq = 0.0

        for term, term_frequency in query_frequencies.items():
            idf = self.idf.get(term)
            if idf is None:
                continue

            query_weight = float((1.0 + log(term_frequency)) * idf)
            query_norm_sq += query_weight * query_weight
            for document_index, document_weight in self.postings.get(term, []):
                scores[document_index] += query_weight * document_weight
                matches[document_index].add(term)

        query_norm = sqrt(query_norm_sq)
        if query_norm == 0:
            return np.zeros(self.document_count, dtype=np.float32), {}

        denominators = self.doc_norms * query_norm
        valid = denominators > 0
        scores[valid] = scores[valid] / denominators[valid]
        normalized_matches = {
            document_id: sorted(terms) for document_id, terms in matches.items()
        }
        return scores, normalized_matches


@dataclass(slots=True)
class ClassicalSearchEngine:
    """Motor híbrido de términos normalizados y expansión por lema."""

    surface_index: InvertedTfidfIndex
    lemma_index: InvertedTfidfIndex
    surface_weight: float
    lemma_weight: float

    @classmethod
    def build(
        cls,
        chunks: list[Chunk],
        *,
        surface_weight: float,
        lemma_weight: float,
    ) -> "ClassicalSearchEngine":
        surface_index = InvertedTfidfIndex.build(
            "surface", [chunk.surface_tokens for chunk in chunks]
        )
        lemma_index = InvertedTfidfIndex.build(
            "lemma", [chunk.lemma_tokens for chunk in chunks]
        )
        return cls(
            surface_index=surface_index,
            lemma_index=lemma_index,
            surface_weight=surface_weight,
            lemma_weight=lemma_weight,
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClassicalSearchEngine":
        return cls(
            surface_index=InvertedTfidfIndex.from_dict(payload["surface_index"]),
            lemma_index=InvertedTfidfIndex.from_dict(payload["lemma_index"]),
            surface_weight=float(payload["surface_weight"]),
            lemma_weight=float(payload["lemma_weight"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "surface_index": self.surface_index.to_dict(),
            "lemma_index": self.lemma_index.to_dict(),
            "surface_weight": self.surface_weight,
            "lemma_weight": self.lemma_weight,
        }

    def search(
        self, query: str, analysis: TextAnalysis, chunks: list[Chunk], top_k: int
    ) -> list[SearchResult]:
        """Ejecuta una búsqueda clásica y agrega los distintos subíndices."""

        surface_scores, surface_matches = self.surface_index.score(
            analysis.surface_tokens
        )
        lemma_scores, lemma_matches = self.lemma_index.score(analysis.lemma_tokens)
        scores = (self.surface_weight * surface_scores) + (
            self.lemma_weight * lemma_scores
        )

        ranked_indices = np.argsort(scores)[::-1]
        query_terms = list(
            dict.fromkeys(analysis.surface_tokens + analysis.lemma_tokens)
        )

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
                    fragment=extract_fragment(chunk.text, [query, *query_terms]),
                    text=chunk.text,
                    metadata={
                        "chunk_word_count": chunk.word_count,
                        "paragraph_span": f"{chunk.start_paragraph}-{chunk.end_paragraph}",
                        "paragraph_count": chunk.metadata.get("paragraph_count"),
                    },
                    explanation={
                        "mode": "classical",
                        "surface_score": round(
                            float(surface_scores[document_index]), 6
                        ),
                        "lemma_score": round(float(lemma_scores[document_index]), 6),
                        "matched_surface_terms": surface_matches.get(
                            int(document_index), []
                        ),
                        "matched_lemma_terms": lemma_matches.get(
                            int(document_index), []
                        ),
                        "query": query,
                    },
                )
            )
            if len(results) >= top_k:
                break

        return results
