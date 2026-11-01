"""AI subsystem for Brazil Election Insights powered by Hugging Face and Qwen3.5-4B."""

from election_research.ai.assistant import ElectionAIAssistant
from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.context_manager import ContextManager
from election_research.ai.conversation import Conversation
from election_research.ai.exceptions import (
    AIConfigurationError,
    AIError,
    AuthenticationError,
    ModelUnavailableError,
    ProviderUnavailableError,
)
from election_research.ai.provider import AIProvider
from election_research.ai.provider_factory import create_ai_provider, get_cached_ai_provider
from election_research.ai.schemas import (
    ChatMessage,
    ModelResponse,
    ProviderHealth,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from election_research.ai.tool_executor import ToolExecutor
from election_research.ai.tool_registry import TOOL_DEFINITIONS, ToolRegistry

__all__ = [
    "ElectionAIAssistant",
    "AIProvider",
    "AISettings",
    "get_ai_settings",
    "create_ai_provider",
    "get_cached_ai_provider",
    "ToolRegistry",
    "ToolExecutor",
    "TOOL_DEFINITIONS",
    "ChatMessage",
    "ToolCall",
    "ToolResult",
    "ModelResponse",
    "ProviderHealth",
    "ToolDefinition",
    "Conversation",
    "ContextManager",
    "AIError",
    "AIConfigurationError",
    "AuthenticationError",
    "ModelUnavailableError",
    "ProviderUnavailableError",
]
