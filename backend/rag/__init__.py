"""RAG module — Vector search for rule grounding and narrative patterns."""

from .retriever import RuleRetriever
from .vector_store import VectorStore
from .embeddings import EmbeddingGenerator

__all__ = ["RuleRetriever", "VectorStore", "EmbeddingGenerator"]
