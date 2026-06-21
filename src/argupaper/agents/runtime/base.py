"""Agent base class for multi-agent debate system."""

import json
from abc import ABC, abstractmethod
from pydantic import BaseModel


class AgentConfig(BaseModel):
    """Configuration for an agent."""
    name: str
    role: str
    max_tokens: int = 2048
    temperature: float = 0.7


class AgentBase(ABC):
    """Base class for all agents in the debate system."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._message_history: list[dict] = []
        self._warnings: list[str] = []

    @abstractmethod
    async def think(self, context: dict) -> str:
        """Process context and return agent's response."""
        pass

    def add_message(self, role: str, content: str) -> None:
        """Add a message to agent's history."""
        self._message_history.append({"role": role, "content": content})

    def clear_history(self) -> None:
        """Clear message history."""
        self._message_history.clear()

    def add_warning(self, message: str) -> None:
        """Record one role-level warning."""

        cleaned = message.strip()
        if cleaned and cleaned not in self._warnings:
            self._warnings.append(cleaned)

    def consume_warnings(self) -> list[str]:
        """Return and clear pending role-level warnings."""

        warnings = self._warnings.copy()
        self._warnings.clear()
        return warnings

    def format_context_value(self, value: object, limit: int = 3000) -> str:
        """Format context data for prompt input."""

        try:
            text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
        except TypeError:
            text = str(value)
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    @property
    def history(self) -> list[dict]:
        """Get message history."""
        return self._message_history.copy()

    @property
    def warnings(self) -> list[str]:
        """Get pending role-level warnings."""

        return self._warnings.copy()
