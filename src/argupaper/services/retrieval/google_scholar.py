"""Google Scholar retrieval through SerpApi."""

import re
from typing import Optional

import aiohttp


class GoogleScholarClient:
    """Client for SerpApi's Google Scholar engine."""

    API_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: Optional[str] = None, api_url: str = API_URL):
        self.api_key = api_key
        self.api_url = api_url

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search Google Scholar through SerpApi."""

        if not self.api_key:
            raise RuntimeError("SERPAPI_API_KEY is not configured for Google Scholar search.")

        params = {
            "engine": "google_scholar",
            "q": query,
            "api_key": self.api_key,
            "num": min(max(limit, 1), 20),
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.api_url, params=params) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"SerpApi Google Scholar returned {resp.status}")
                payload = await resp.json()

        if payload.get("error"):
            raise RuntimeError(f"SerpApi Google Scholar error: {payload['error']}")

        results: list[dict] = []
        for item in payload.get("organic_results", [])[:limit]:
            publication_info = item.get("publication_info") or {}
            summary = str(publication_info.get("summary") or "")
            inline_links = item.get("inline_links") or {}
            cited_by = inline_links.get("cited_by") or {}

            results.append(
                {
                    "title": item.get("title") or "Untitled",
                    "authors": self._extract_authors(publication_info),
                    "year": self._extract_year(summary),
                    "venue": self._extract_venue(summary),
                    "citation_count": int(cited_by.get("total") or 0),
                    "url": item.get("link") or "",
                    "source": "google_scholar",
                    "abstract": item.get("snippet"),
                }
            )
        return results

    def _extract_authors(self, publication_info: dict) -> list[str]:
        authors = publication_info.get("authors") or []
        normalized = [
            str(author.get("name") or "").strip()
            for author in authors
            if str(author.get("name") or "").strip()
        ]
        if normalized:
            return normalized

        summary = str(publication_info.get("summary") or "")
        author_part = summary.split(" - ", 1)[0]
        return [item.strip() for item in author_part.split(",") if item.strip()][:6]

    def _extract_year(self, summary: str) -> int | None:
        years = [int(match) for match in re.findall(r"\b(?:19|20)\d{2}\b", summary)]
        if not years:
            return None
        return max(years)

    def _extract_venue(self, summary: str) -> str:
        parts = [part.strip() for part in summary.split(" - ") if part.strip()]
        if len(parts) >= 2:
            return parts[1]
        return "Google Scholar"
