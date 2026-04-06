"""Pipeline de normalización lingüística compartido por corpus y consulta."""

from __future__ import annotations

from collections.abc import Iterable
import re

from p4.app.config import custom_stopwords
from p4.app.errors import ConfigurationError
from p4.app.models import TextAnalysis
from p4.app.utils import normalize_token, normalize_whitespace


INVALID_CHARS_RE = re.compile(r"[\d_]+", flags=re.UNICODE)


class SpanishTextPreprocessor:
    """Preprocesa texto en español con spaCy y stopwords custom."""

    def __init__(self, spacy_model: str) -> None:
        self.spacy_model = spacy_model
        self._nlp = None
        self._stopwords = {normalize_token(word) for word in custom_stopwords()}

    @property
    def nlp(self):  # pragma: no cover - depende de la instalación local.
        if self._nlp is None:
            try:
                import spacy
            except ImportError as exc:  # pragma: no cover - depende del entorno.
                raise ConfigurationError(
                    "spaCy no está instalado. Instala las dependencias de p4 antes de ejecutar la app."
                ) from exc

            try:
                self._nlp = spacy.load(self.spacy_model, disable=["ner", "parser"])
            except OSError as exc:
                raise ConfigurationError(
                    "No se encontró el modelo de spaCy "
                    f"{self.spacy_model!r}. Instálalo con: python -m spacy download {self.spacy_model}"
                ) from exc
        return self._nlp

    def analyze(self, text: str) -> TextAnalysis:
        """Procesa un único texto."""

        cleaned_text = self._clean_text(text)
        doc = self.nlp(cleaned_text)
        return self._analysis_from_doc(text, cleaned_text, doc)

    def analyze_many(
        self, texts: Iterable[str], batch_size: int = 32
    ) -> list[TextAnalysis]:
        """Procesa varios textos usando `nlp.pipe` para acelerar el corpus."""

        originals = list(texts)
        cleaned = [self._clean_text(text) for text in originals]
        analyses: list[TextAnalysis] = []
        for original, cleaned_text, doc in zip(
            originals, cleaned, self.nlp.pipe(cleaned, batch_size=batch_size)
        ):
            analyses.append(self._analysis_from_doc(original, cleaned_text, doc))
        return analyses

    def _analysis_from_doc(
        self, original_text: str, cleaned_text: str, doc
    ) -> TextAnalysis:
        surface_tokens: list[str] = []
        lemma_tokens: list[str] = []

        for token in doc:
            if (
                token.is_space
                or token.is_punct
                or token.pos_ in {"PUNCT", "SPACE", "SYM", "X"}
            ):
                continue

            surface = normalize_token(token.text)
            lemma_source = (
                token.lemma_
                if token.lemma_ and token.lemma_ != "-PRON-"
                else token.text
            )
            lemma = normalize_token(lemma_source)
            if not surface and not lemma:
                continue

            canonical = lemma or surface
            if len(canonical) < 2:
                continue
            if INVALID_CHARS_RE.fullmatch(canonical):
                continue
            if (
                surface in self._stopwords
                or canonical in self._stopwords
                or token.is_stop
            ):
                continue
            if not any(char.isalpha() for char in canonical):
                continue

            surface_tokens.append(surface or canonical)
            lemma_tokens.append(canonical)

        return TextAnalysis(
            original_text=original_text,
            cleaned_text=cleaned_text,
            surface_tokens=surface_tokens,
            lemma_tokens=lemma_tokens,
        )

    @staticmethod
    def _clean_text(text: str) -> str:
        cleaned = text.lower()
        cleaned = cleaned.replace("—", " ").replace("–", " ").replace("’", "'")
        cleaned = re.sub(r"[^\w\sáéíóúüñ']", " ", cleaned, flags=re.UNICODE)
        cleaned = normalize_whitespace(cleaned)
        return cleaned
