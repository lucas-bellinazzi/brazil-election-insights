"""Unit tests for AI configuration and settings validation."""

import pytest
from pydantic import ValidationError

from election_research.ai.config import AISettings
from election_research.ai.exceptions import AIConfigurationError


def test_ai_settings_defaults():
    settings = AISettings()
    assert settings.ai_enabled is True
    assert settings.ai_provider == "huggingface"
    assert settings.ai_model_id == "Qwen/Qwen3.5-4B"
    assert settings.ai_temperature == 0.2
    assert settings.ai_max_new_tokens == 2048
    assert settings.ai_request_timeout == 120
    assert settings.ai_max_tool_iterations == 5
    assert settings.ai_max_conversation_messages == 12
    assert settings.ai_enable_thinking is False


def test_ai_settings_endpoint_validation():
    # huggingface_endpoint requires hf_endpoint_url
    settings = AISettings(ai_provider="huggingface_endpoint", hf_endpoint_url=None)
    with pytest.raises(AIConfigurationError, match="HF_ENDPOINT_URL is required"):
        settings.validate_provider_requirements()

    valid_endpoint = AISettings(
        ai_provider="huggingface_endpoint",
        hf_endpoint_url="https://mock-endpoint.endpoints.huggingface.cloud",
    )
    valid_endpoint.validate_provider_requirements()


def test_ai_settings_temperature_bounds():
    with pytest.raises(ValidationError):
        AISettings(ai_temperature=3.5)  # Max is 2.0

