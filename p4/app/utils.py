"""Utilidades compartidas del proyecto."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
import re
import unicodedata


WHITESPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\w+", flags=re.UNICODE)


def normalize_whitespace(text: str) -> str:
    """Reduce secuencias de espacios y saltos de línea."""

    return WHITESPACE_RE.sub(" ", text).strip()


def strip_accents(text: str) -> str:
    """Elimina diacríticos manteniendo la longitud lógica de las palabras."""

    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_token(token: str) -> str:
    """Normaliza un token para indexado y comparación."""

    token = strip_accents(token.lower())
    token = re.sub(r"[^\w]+", "", token, flags=re.UNICODE)
    return token.strip("_")


def count_words(text: str) -> int:
    """Cuenta palabras aproximadas a partir de caracteres alfanuméricos."""

    return len(WORD_RE.findall(text))


def sha256_of_file(path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo."""

    digest = sha256()
    with path.open("rb") as handler:
        for block in iter(lambda: handler.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def utc_now_iso() -> str:
    """Devuelve la hora actual en ISO 8601 con zona UTC."""

    return datetime.now(UTC).isoformat()


def batched(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    """Divide una secuencia en bloques de tamaño fijo."""

    if size <= 0:
        raise ValueError("size debe ser mayor que cero")
    for index in range(0, len(items), size):
        yield items[index : index + size]


def extract_fragment(text: str, candidates: Iterable[str], max_chars: int = 360) -> str:
    """Extrae un fragmento centrado en el primer término coincidente."""

    clean_text = normalize_whitespace(text)
    if not clean_text:
        return ""

    folded_text = strip_accents(clean_text.lower())
    normalized_terms = [strip_accents(term.lower()) for term in candidates if term]

    best_position = len(clean_text)
    for term in normalized_terms:
        if len(term) < 2:
            continue
        position = folded_text.find(term)
        if position >= 0:
            best_position = min(best_position, position)

    if best_position == len(clean_text):
        best_position = 0

    start = max(0, best_position - max_chars // 4)
    end = min(len(clean_text), start + max_chars)
    fragment = clean_text[start:end]
    if start > 0:
        fragment = "..." + fragment
    if end < len(clean_text):
        fragment = fragment + "..."
    return fragment
