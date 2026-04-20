"""Conversation memory for context management."""

from typing import Optional


class ConversationMemory:
    """Memory for conversation context across tasks."""

    def __init__(self):
        self._context: dict = {}

    def add_turn(self, role: str, content: str) -> None:
        """Add a conversation turn."""
        raise NotImplementedError("To be implemented")

    def get_context(self) -> dict:
        """Get current conversation context."""
        raise NotImplementedError("To be implemented")

    def clear(self) -> None:
        """Clear conversation memory."""
        self._context.clear()