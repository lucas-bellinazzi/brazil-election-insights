"""Custom domain exceptions for the Hugging Face AI subsystem."""

from election_research.core.exceptions import ElectionResearchError


class AIError(ElectionResearchError):
    """Base exception for all AI subsystem errors."""


class AIConfigurationError(AIError):
    """Raised when AI configuration or environment variables are missing or invalid."""


class AuthenticationError(AIError):
    """Raised when Hugging Face token is missing, invalid, or lacks necessary permissions."""


class ModelUnavailableError(AIError):
    """Raised when the requested model (e.g., Qwen/Qwen3.5-4B) cannot be reached or loaded."""


class ProviderUnavailableError(AIError):
    """Raised when the selected Hugging Face Inference Provider is unreachable or unsupported."""


class EndpointUnavailableError(AIError):
    """Raised when a dedicated Hugging Face Inference Endpoint is offline or returns error."""


class RequestTimeoutError(AIError):
    """Raised when an inference or tool request exceeds the configured timeout."""


class RateLimitError(AIError):
    """Raised when the provider enforces request or rate limits."""


class QuotaExceededError(AIError):
    """Raised when account or inference provider quota is exhausted."""


class InvalidResponseError(AIError):
    """Raised when the model output cannot be parsed or violates schema expectations."""


class InvalidToolCallError(AIError):
    """Raised when a model-generated tool call is malformed, unrecognized, or unauthorized."""


class ToolExecutionError(AIError):
    """Raised when executing an analytical tool fails."""


class ContextLengthExceededError(AIError):
    """Raised when conversation or tool payload exceeds context limits."""
