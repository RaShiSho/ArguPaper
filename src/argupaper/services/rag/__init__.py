"""Local RAG service configuration and initialization boundary."""

from argupaper.services.rag.chunker import PaperChunk, PaperChunker
from argupaper.services.rag.config import MilvusConfig, OllamaEmbeddingConfig, RAGConfig
from argupaper.services.rag.context_builder import ContextBuilder
from argupaper.services.rag.embedding import OllamaEmbeddingClient
from argupaper.services.rag.indexer import RAGIndexer, RAGIndexStats
from argupaper.services.rag.init import (
    RAGServiceSettings,
    build_context_builder,
    build_milvus_vector_store,
    build_ollama_embedding_client,
    build_paper_chunker,
    build_rag_indexer,
    build_rag_retriever,
    build_rag_service_settings,
)
from argupaper.services.rag.parser import PaperTextParser, ParsedPaperText, ParsedSection
from argupaper.services.rag.retriever import (
    RAGRetriever,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)
from argupaper.services.rag.vector_store import MilvusChunk, MilvusSearchResult, MilvusVectorStore

__all__ = [
    "ContextBuilder",
    "MilvusChunk",
    "MilvusConfig",
    "MilvusSearchResult",
    "MilvusVectorStore",
    "OllamaEmbeddingClient",
    "OllamaEmbeddingConfig",
    "PaperChunk",
    "PaperChunker",
    "PaperTextParser",
    "ParsedPaperText",
    "ParsedSection",
    "RAGConfig",
    "RAGIndexer",
    "RAGIndexStats",
    "RAGRetriever",
    "RAGServiceSettings",
    "RetrievalQuery",
    "RetrievalResult",
    "RetrievedChunk",
    "build_context_builder",
    "build_milvus_vector_store",
    "build_ollama_embedding_client",
    "build_paper_chunker",
    "build_rag_indexer",
    "build_rag_retriever",
    "build_rag_service_settings",
]
