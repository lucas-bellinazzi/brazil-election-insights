"""Abstract base interface for AI model inference providers."""

from abc import ABC, abstractmethod
from collections.abc import Sequence

from election_research.ai.schemas import ChatMessage, ModelResponse, ProviderHealth, ToolDefinition


class AIProvider(ABC):
    """Abstract interface for all Hugging Face and local model inference adapters."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Return provider identifier (e.g., 'huggingface', 'huggingface_endpoint', 'local')."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Return model repository identifier (e.g., 'Qwen/Qwen3.5-4B')."""

    @abstractmethod
    def generate_response(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition] | None = None,
    ) -> ModelResponse:
        """Send chat messages and tool definitions to the model and return structured response."""

    @abstractmethod
    def health_check(self) -> ProviderHealth:
        """Perform a lightweight connectivity and capability test."""
