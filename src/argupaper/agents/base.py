"""Agent base class for multi-agent debate system."""

from abc import ABC, abstractmethod
from typing import Optional
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

    @property
    def history(self) -> list[dict]:
        """Get message history."""
        return self._message_history.copy()