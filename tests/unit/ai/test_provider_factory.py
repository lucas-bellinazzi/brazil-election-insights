"""Unit tests for AI provider factory and provider instantiation."""

from election_research.ai.config import AISettings
from election_research.ai.provider_factory import create_ai_provider
from election_research.ai.providers.huggingface_endpoint import HuggingFaceEndpointProvider
from election_research.ai.providers.huggingface_inference import HuggingFaceInferenceProvider
from election_research.ai.providers.local_inference import LocalInferenceProvider


def test_create_huggingface_provider():
    settings = AISettings(ai_provider="huggingface")
    provider = create_ai_provider(settings)
    assert isinstance(provider, HuggingFaceInferenceProvider)
    assert provider.provider_id == "huggingface"
    assert provider.model_id == "Qwen/Qwen3.5-4B"


def test_create_endpoint_provider():
    settings = AISettings(
        ai_provider="huggingface_endpoint",
        hf_endpoint_url="https://mock.endpoints.huggingface.cloud",
    )
    provider = create_ai_provider(settings)
    assert isinstance(provider, HuggingFaceEndpointProvider)
    assert provider.provider_id == "huggingface_endpoint"


def test_create_local_provider():
    settings = AISettings(ai_provider="local")
    provider = create_ai_provider(settings)
    assert isinstance(provider, LocalInferenceProvider)
    assert provider.provider_id == "local"

