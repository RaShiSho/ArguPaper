"""Semantic Scholar API client for paper retrieval."""

from typing import Optional

import aiohttp


class SemanticScholarClient:
    """Client for Semantic Scholar API."""

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search papers by query."""

        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,citationCount,url,abstract,externalIds",
        }
        headers = {"x-api-key": self.api_key} if self.api_key else {}

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/paper/search",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Semantic Scholar returned {resp.status}")
                payload = await resp.json()

        papers: list[dict] = []
        for item in payload.get("data", []):
            url = item.get("url") or ""
            external_ids = item.get("externalIds") or {}
            if not url and external_ids.get("ArXiv"):
                url = f"https://arxiv.org/abs/{external_ids['ArXiv']}"

            papers.append(
                {
                    "title": item.get("title") or "Untitled",
                    "authors": [author.get("name", "Unknown") for author in item.get("authors", [])],
                    "year": item.get("year"),
                    "venue": item.get("venue") or "Semantic Scholar",
                    "citation_count": item.get("citationCount") or 0,
                    "url": url,
                    "source": "semantic_scholar",
                    "abstract": item.get("abstract"),
                }
            )
        return papers

    async def get_paper(self, paper_id: str) -> dict:
        """Get paper details by ID."""

        headers = {"x-api-key": self.api_key} if self.api_key else {}
        params = {"fields": "title,authors,year,venue,citationCount,url,abstract"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/paper/{paper_id}",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Semantic Scholar returned {resp.status}")
                return await resp.json()

    async def get_references(self, paper_id: str) -> list[dict]:
        """Get references for a paper."""

        headers = {"x-api-key": self.api_key} if self.api_key else {}
        params = {"fields": "title,authors,year,venue,citationCount,url"}
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.BASE_URL}/paper/{paper_id}/references",
                params=params,
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Semantic Scholar returned {resp.status}")
                payload = await resp.json()
        return payload.get("data", [])
