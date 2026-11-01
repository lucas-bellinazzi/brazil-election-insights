"""AI provider abstraction and OpenAI implementation."""

import json
from abc import ABC, abstractmethod
from typing import Any

from openai import OpenAI

from election_research.core.config import get_settings
from election_research.core.exceptions import AIProviderError
from election_research.core.logging import get_logger
from election_research.core.security import redact_sensitive_text

logger = get_logger(__name__)


class AIProvider(ABC):
    """Abstract interface for AI chat and tool-calling providers."""

    @abstractmethod
    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate a model response with optional tool calling."""


class OpenAIProvider(AIProvider):
    """OpenAI API implementation using official SDK."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def chat_completion(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Generate response or tool calls via OpenAI Chat API."""
        if not self.client:
            raise AIProviderError(
                "Chave OPENAI_API_KEY não configurada. Configure a variável no arquivo .env."
            )

        try:
            kwargs: dict[str, Any] = {
                "model": self.model,
                "messages": messages,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            tool_calls = []
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append(
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": json.loads(tc.function.arguments),
                            },
                        }
                    )

            return {
                "role": "assistant",
                "content": message.content,
                "tool_calls": tool_calls if tool_calls else None,
            }
        except Exception as e:
            sanitized_err = redact_sensitive_text(str(e))
            raise AIProviderError(f"Erro na comunicação com OpenAI: {sanitized_err}") from e
