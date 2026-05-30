"""Academic paper retrieval services."""

from argupaper.services.retrieval.arxiv import ArXivClient
from argupaper.services.retrieval.google_scholar import GoogleScholarClient
from argupaper.services.retrieval.query_expansion import QueryExpander
from argupaper.services.retrieval.semantic_scholar import SemanticScholarClient

__all__ = [
    "ArXivClient",
    "GoogleScholarClient",
    "QueryExpander",
    "SemanticScholarClient",
]

