"""Carga y extracción del corpus fuente."""

from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from p4.app.models import Document, Paragraph
from p4.app.utils import count_words, normalize_whitespace


END_OF_BOOK_MARKER = "*** END OF THE PROJECT GUTENBERG EBOOK"


def load_html(path: Path) -> BeautifulSoup:
    """Lee el HTML del corpus y devuelve el árbol parseado."""

    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def extract_documents(path: Path, ignored_ids: set[str]) -> list[Document]:
    """Extrae los capítulos del Quijote desde el HTML fuente."""

    soup = load_html(path)
    sections: list[tuple[str, str, object]] = []

    for heading in soup.find_all("h3"):
        anchor = heading.find("a", attrs={"name": True})
        if anchor is None:
            continue
        sections.append(
            (
                anchor["name"],
                normalize_whitespace(heading.get_text(" ", strip=True)),
                heading,
            )
        )

    documents: list[Document] = []
    for section_id, title, element in sections:
        if section_id in ignored_ids:
            continue

        paragraphs: list[Paragraph] = []
        sibling = element.find_next_sibling()
        while sibling is not None:
            if sibling.name in {"h2", "h3"} and sibling.find("a", attrs={"name": True}):
                break

            text = normalize_whitespace(sibling.get_text(" ", strip=True))
            if END_OF_BOOK_MARKER in text:
                break
            if text:
                paragraph_index = len(paragraphs)
                paragraphs.append(
                    Paragraph(
                        paragraph_id=f"{section_id}::p{paragraph_index:03d}",
                        document_id=section_id,
                        order=paragraph_index,
                        text=text,
                        word_count=count_words(text),
                    )
                )
            sibling = sibling.find_next_sibling()

        if not paragraphs:
            continue

        part = "I" if section_id.startswith("1_") else "II"
        total_words = sum(paragraph.word_count for paragraph in paragraphs)
        documents.append(
            Document(
                document_id=section_id,
                part=part,
                title=title,
                paragraphs=paragraphs,
                source_path=str(path),
                metadata={
                    "paragraph_count": len(paragraphs),
                    "word_count": total_words,
                },
            )
        )

    return documents
