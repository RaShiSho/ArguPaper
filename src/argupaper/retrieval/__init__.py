"""Academic paper retrieval module."""

from argupaper.retrieval.arxiv import ArXivClient
from argupaper.retrieval.google_scholar import GoogleScholarClient
from argupaper.retrieval.query_expansion import QueryExpander
from argupaper.retrieval.semantic_scholar import SemanticScholarClient

__all__ = [
    "ArXivClient",
    "GoogleScholarClient",
    "QueryExpander",
    "SemanticScholarClient",
]
