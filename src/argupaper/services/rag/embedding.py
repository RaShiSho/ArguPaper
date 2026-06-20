"""Ollama embedding client for local RAG."""

from __future__ import annotations

from typing import Any, Optional

import aiohttp

from argupaper.services.rag.config import OllamaEmbeddingConfig
from argupaper.workflows.errors import ExternalServiceError, InputValidationError


class OllamaEmbeddingClient:
    """Async client for Ollama's `/api/embed` endpoint."""

    def __init__(self, config: OllamaEmbeddingConfig, *, timeout_seconds: int = 60) -> None:
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._session: Optional[aiohttp.ClientSession] = None

    async def embed_text(self, text: str) -> list[float]:
        """Generate one embedding for a single text."""

        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for one or more texts."""

        cleaned_texts = self._validate_texts(texts)
        payload = {
            "model": self.config.model,
            "input": cleaned_texts[0] if len(cleaned_texts) == 1 else cleaned_texts,
        }
        data = await self._post_embed(payload)
        embeddings = self._parse_embeddings(data)
        if len(embeddings) != len(cleaned_texts):
            raise ExternalServiceError(
                "Ollama embedding response count does not match input count: "
                f"expected {len(cleaned_texts)}, got {len(embeddings)}."
            )
        return embeddings

    async def close(self) -> None:
        """Close the underlying HTTP session."""

        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                trust_env=True,
            )
        return self._session

    async def _post_embed(self, payload: dict[str, Any]) -> dict[str, Any]:
        session = await self._get_session()
        endpoint = f"{self.config.base_url.rstrip('/')}/api/embed"
        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        try:
            async with session.post(endpoint, json=payload, timeout=timeout) as response:
                body = await response.text()
                if response.status >= 400:
                    raise ExternalServiceError(
                        f"Ollama embedding endpoint returned {response.status}: {body}"
                    )
                try:
                    data = await response.json()
                except (aiohttp.ContentTypeError, ValueError) as exc:
                    raise ExternalServiceError(
                        "Ollama embedding endpoint returned invalid JSON."
                    ) from exc
        except aiohttp.ClientError as exc:
            raise ExternalServiceError(
                f"Ollama embedding request failed at {endpoint}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ExternalServiceError("Ollama embedding endpoint returned a non-object payload.")
        return data

    def _validate_texts(self, texts: list[str]) -> list[str]:
        if not texts:
            raise InputValidationError("Embedding input must contain at least one text.")

        cleaned: list[str] = []
        for index, text in enumerate(texts):
            if not isinstance(text, str):
                raise InputValidationError(f"Embedding input at index {index} must be a string.")
            normalized = text.strip()
            if not normalized:
                raise InputValidationError(f"Embedding input at index {index} is empty.")
            cleaned.append(normalized)
        return cleaned

    def _parse_embeddings(self, data: dict[str, Any]) -> list[list[float]]:
        raw_embeddings = data.get("embeddings")
        if not isinstance(raw_embeddings, list):
            raise ExternalServiceError("Ollama embedding response is missing `embeddings`.")

        embeddings: list[list[float]] = []
        for embedding_index, raw_embedding in enumerate(raw_embeddings):
            if not isinstance(raw_embedding, list):
                raise ExternalServiceError(
                    f"Ollama embedding at index {embedding_index} is not a list."
                )
            embedding: list[float] = []
            for value_index, value in enumerate(raw_embedding):
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise ExternalServiceError(
                        "Ollama embedding response contains a non-numeric value "
                        f"at embedding {embedding_index}, index {value_index}."
                    )
                embedding.append(float(value))
            if not embedding:
                raise ExternalServiceError(f"Ollama embedding at index {embedding_index} is empty.")
            embeddings.append(embedding)

        if not embeddings:
            raise ExternalServiceError("Ollama embedding response contains no embeddings.")
        return embeddings


__all__ = ["OllamaEmbeddingClient"]
