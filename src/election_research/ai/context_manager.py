"""Context and token management for Qwen3.5-4B inference budgets."""

import json

from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.prompts import SYSTEM_PROMPT
from election_research.ai.schemas import ChatMessage, ToolResult
from election_research.core.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """Controls message sliding windows, trims oversized tool results, and fits context budgets."""

    def __init__(self, settings: AISettings | None = None) -> None:
        self.settings = settings or get_ai_settings()
        self.max_messages = self.settings.ai_max_conversation_messages
        self.max_tool_records = self.settings.ai_max_tool_result_records

    def build_prompt_messages(
        self,
        history: list[ChatMessage],
        current_user_message: str | None = None,
    ) -> list[ChatMessage]:
        """Construct the prompt message list ensuring System Prompt is first and history is bounded."""
        messages: list[ChatMessage] = [ChatMessage(role="system", content=SYSTEM_PROMPT)]

        # Extract non-system history messages
        user_assistant_msgs = [m for m in history if m.role != "system"]

        # Apply sliding window keeping the latest (max_messages - 1) turns
        if len(user_assistant_msgs) > (self.max_messages - 1):
            trimmed_msgs = user_assistant_msgs[-(self.max_messages - 1) :]
            logger.debug(
                "Trimmed conversation history from %d to %d messages",
                len(user_assistant_msgs),
                len(trimmed_msgs),
            )
            messages.extend(trimmed_msgs)
        else:
            messages.extend(user_assistant_msgs)

        if current_user_message:
            messages.append(ChatMessage(role="user", content=current_user_message))

        return messages

    def format_tool_result_content(self, result: ToolResult) -> str:
        """Format a ToolResult into a compact, bounded JSON payload for the model context."""
        summary = result.to_summary_dict()

        # If data is a list of records, bound it to max_tool_records
        data = summary.get("data")
        if isinstance(data, list) and len(data) > self.max_tool_records:
            original_len = len(data)
            summary["data"] = data[: self.max_tool_records]
            summary["truncation_notice"] = (
                f"Mostrando {self.max_tool_records} de {original_len} registros retornados."
            )

        try:
            return json.dumps(summary, ensure_ascii=False)
        except Exception:
            return str(summary)
