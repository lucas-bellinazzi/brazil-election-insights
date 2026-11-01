"""Conversation state and history management for interactive multi-turn sessions."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from election_research.ai.schemas import ChatMessage, ToolCall, ToolResult


@dataclass
class ConversationTurn:
    """A single turn in the conversation session."""

    turn_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    user_message: str = ""
    assistant_response: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_results: list[ToolResult] = field(default_factory=list)


class Conversation:
    """Manages sequential chat turns and structured message representations."""

    def __init__(self, conversation_id: str | None = None) -> None:
        self.conversation_id: str = conversation_id or uuid.uuid4().hex
        self.messages: list[ChatMessage] = []
        self.turns: list[ConversationTurn] = []
        self.metadata: dict[str, Any] = {}

    def add_message(self, message: ChatMessage) -> None:
        """Append a message to the internal message list."""
        self.messages.append(message)

    def add_user_message(self, content: str) -> None:
        """Record a user query."""
        self.messages.append(ChatMessage(role="user", content=content))

    def add_assistant_message(
        self,
        content: str,
        tool_calls: list[ToolCall] | None = None,
    ) -> None:
        """Record an assistant response with optional tool calls."""
        self.messages.append(ChatMessage(role="assistant", content=content, tool_calls=tool_calls))

    def add_tool_result(self, tool_call_id: str, tool_name: str, content: str) -> None:
        """Record the structured output of an executed tool."""
        self.messages.append(
            ChatMessage(
                role="tool",
                content=content,
                tool_call_id=tool_call_id,
                name=tool_name,
            )
        )

    def clear(self) -> None:
        """Reset conversation state."""
        self.messages.clear()
        self.turns.clear()
        self.metadata.clear()

    def get_messages(self) -> list[ChatMessage]:
        """Return full history of messages."""
        return list(self.messages)
