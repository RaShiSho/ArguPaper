"""ArXiv API client for paper retrieval."""

from pathlib import Path
from xml.etree import ElementTree

import aiohttp


class ArXivClient:
    """Client for ArXiv API."""

    API_URL = "http://export.arxiv.org/api/query"
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search papers by query."""

        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": limit,
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(self.API_URL, params=params) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"arXiv returned {resp.status}")
                xml_payload = await resp.text()

        root = ElementTree.fromstring(xml_payload)
        results: list[dict] = []
        for entry in root.findall("atom:entry", self.ATOM_NS):
            title = (entry.findtext("atom:title", default="", namespaces=self.ATOM_NS) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=self.ATOM_NS) or "").strip()
            published = entry.findtext("atom:published", default="", namespaces=self.ATOM_NS)
            year = int(published[:4]) if published and len(published) >= 4 else None
            authors = [
                (author.findtext("atom:name", default="", namespaces=self.ATOM_NS) or "").strip()
                for author in entry.findall("atom:author", self.ATOM_NS)
            ]
            url = entry.findtext("atom:id", default="", namespaces=self.ATOM_NS) or ""
            results.append(
                {
                    "title": title or "Untitled",
                    "authors": authors,
                    "year": year,
                    "venue": "arXiv",
                    "citation_count": 0,
                    "url": url,
                    "source": "arxiv",
                    "abstract": summary or None,
                }
            )
        return results

    async def download_pdf(self, paper_id: str, save_path: str) -> str:
        """Download paper PDF to local path."""

        pdf_url = f"https://arxiv.org/pdf/{paper_id}.pdf"
        destination = Path(save_path)
        destination.parent.mkdir(parents=True, exist_ok=True)

        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"arXiv PDF download returned {resp.status}")
                destination.write_bytes(await resp.read())

        return str(destination)
