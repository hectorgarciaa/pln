"""Componentes del flujo RAG sobre recuperación híbrida + Ollama."""

from p4.app.rag.context_builder import ContextBuilder, RagContext
from p4.app.rag.formatter import format_rag_answer_markdown, referenced_sources
from p4.app.rag.generator import OllamaRagGenerator
from p4.app.rag.retriever import HybridRetriever

__all__ = [
    "ContextBuilder",
    "HybridRetriever",
    "OllamaRagGenerator",
    "RagContext",
    "format_rag_answer_markdown",
    "referenced_sources",
]
