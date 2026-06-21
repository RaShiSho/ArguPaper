"""OpenAI-compatible LLM client utilities."""

from __future__ import annotations

import json
from typing import Optional

import aiohttp

from argupaper.config import LLMProviderConfig, ModelConfig
from argupaper.workflows.errors import ConfigurationError, ExternalServiceError


class OpenAICompatibleLLMClient:
    """Small client for OpenAI-compatible chat completion APIs."""

    def __init__(self, provider: LLMProviderConfig):
        self.provider = provider
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.provider.api_key}",
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def chat(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Run a chat-completion request and return the text content."""

        session = await self._get_session()
        payload = {
            "model": self.provider.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        endpoint = f"{self.provider.base_url}/chat/completions"
        timeout = aiohttp.ClientTimeout(total=45)

        try:
            async with session.post(endpoint, json=payload, timeout=timeout) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise ExternalServiceError(
                        f"LLM provider '{self.provider.name}' returned {response.status}: {body}"
                    )
                data = await response.json()
        except aiohttp.ClientError as exc:
            raise ExternalServiceError(
                f"LLM provider '{self.provider.name}' request failed: {exc}"
            ) from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ExternalServiceError(
                f"LLM provider '{self.provider.name}' returned an invalid response payload."
            ) from exc

        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text", "")))
            return "\n".join(part for part in text_parts if part).strip()

        return str(content).strip()

    async def close(self) -> None:
        """Close the client session."""

        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None


class LLMRouter:
    """Resolve configured OpenAI-compatible providers by alias."""

    def __init__(self, model_config: ModelConfig):
        self.model_config = model_config
        self._clients: dict[str, OpenAICompatibleLLMClient] = {}

    def has_provider(self, alias: str) -> bool:
        provider_name = self._resolve_provider_name(alias)
        return provider_name in self.model_config.providers

    def get_client(self, alias: str) -> OpenAICompatibleLLMClient:
        provider_name = self._resolve_provider_name(alias)
        provider = self.model_config.providers.get(provider_name)
        if provider is None:
            raise ConfigurationError(
                f"LLM provider '{provider_name}' is not configured. "
                "Please update .env with LLM_PROVIDER__<NAME>__BASE_URL/API_KEY/MODEL."
            )
        if provider_name not in self._clients:
            self._clients[provider_name] = OpenAICompatibleLLMClient(provider)
        return self._clients[provider_name]

    async def close(self) -> None:
        """Close all provider clients."""

        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    def _resolve_provider_name(self, alias: str) -> str:
        normalized = alias.strip().lower()
        if normalized == "weak":
            return self.model_config.weak_provider.strip().lower()
        if normalized == "default":
            return self.model_config.default_provider.strip().lower()
        return normalized


def extract_json_object(payload: str) -> dict:
    """Extract the first JSON object from a model response."""

    text = payload.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response does not contain a JSON object.")

    return json.loads(text[start : end + 1])
