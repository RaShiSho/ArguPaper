"""LangChain adapter for the existing OpenAI-compatible LLM router."""

from __future__ import annotations

from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda

from argupaper.llm.client import LLMRouter


def build_llm_router_runnable(
    router: LLMRouter,
    *,
    provider_alias: str = "default",
    temperature: float,
    max_tokens: int,
) -> Runnable[Any, str]:
    """Build an LCEL-compatible runnable backed by the project's LLM router."""

    async def _call(prompt_input: Any) -> str:
        system_prompt, user_prompt = split_prompt_input(prompt_input)
        client = router.get_client(provider_alias)
        return await client.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    return RunnableLambda(_call, name=f"llm-router-{provider_alias}")


def split_prompt_input(prompt_input: Any) -> tuple[str, str]:
    """Convert LangChain prompt values into the router's system/user prompt shape."""

    if hasattr(prompt_input, "to_messages"):
        messages = prompt_input.to_messages()
    elif isinstance(prompt_input, list):
        messages = prompt_input
    else:
        return "You are a careful research analysis assistant.", str(prompt_input)

    system_parts: list[str] = []
    user_parts: list[str] = []
    for message in messages:
        content = _message_content_to_text(getattr(message, "content", message))
        if not content:
            continue
        role = str(getattr(message, "type", getattr(message, "role", "human"))).lower()
        if role == "system":
            system_parts.append(content)
        else:
            user_parts.append(f"{role}: {content}")

    system_prompt = "\n\n".join(system_parts).strip()
    user_prompt = "\n\n".join(user_parts).strip()
    return (
        system_prompt or "You are a careful research analysis assistant.",
        user_prompt or str(prompt_input),
    )


def _message_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "content" in item:
                    parts.append(str(item.get("content", "")))
            else:
                parts.append(str(item))
        return "\n".join(part.strip() for part in parts if part).strip()
    return str(content).strip()
