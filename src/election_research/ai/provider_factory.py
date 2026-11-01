"""Factory for creating and reusing configured AI model providers."""

from functools import lru_cache

from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.exceptions import AIConfigurationError
from election_research.ai.provider import AIProvider
from election_research.ai.providers.huggingface_endpoint import HuggingFaceEndpointProvider
from election_research.ai.providers.huggingface_inference import HuggingFaceInferenceProvider
from election_research.ai.providers.local_inference import LocalInferenceProvider
from election_research.core.logging import get_logger

logger = get_logger(__name__)


def create_ai_provider(settings: AISettings | None = None) -> AIProvider:
    """Instantiate the AIProvider according to application configuration."""
    cfg = settings or get_ai_settings()
    provider_id = cfg.ai_provider.lower()

    logger.info("Initializing AI Provider '%s' for model '%s'", provider_id, cfg.ai_model_id)

    if provider_id == "huggingface":
        return HuggingFaceInferenceProvider(settings=cfg)
    if provider_id == "huggingface_endpoint":
        return HuggingFaceEndpointProvider(settings=cfg)
    if provider_id == "local":
        return LocalInferenceProvider(settings=cfg)

    raise AIConfigurationError(
        f"Unknown or unsupported AI provider: '{provider_id}'. "
        "Supported values: 'huggingface', 'huggingface_endpoint', 'local'."
    )


@lru_cache(maxsize=1)
def get_cached_ai_provider() -> AIProvider:
    """Return a cached singleton provider instance to avoid redundant client creation."""
    return create_ai_provider()
