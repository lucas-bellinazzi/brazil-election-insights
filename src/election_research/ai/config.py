"""Centralized configuration for the AI subsystem (Hugging Face + Qwen3.5-4B)."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field

from election_research.ai.exceptions import AIConfigurationError
from election_research.core.config import find_project_root


class AISettings(BaseModel):
    """Strongly typed settings for Hugging Face inference and assistant orchestration."""

    model_config = ConfigDict(extra="ignore")

    ai_enabled: bool = Field(default=True)
    ai_provider: Literal["huggingface", "huggingface_endpoint", "local"] = Field(
        default="huggingface"
    )
    ai_model_id: str = Field(default="Qwen/Qwen3.5-4B")

    hf_token: str | None = Field(default=None)
    hf_inference_provider: str | None = Field(default=None)
    hf_endpoint_url: str | None = Field(default=None)

    ai_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    ai_max_new_tokens: int = Field(default=2048, ge=64, le=8192)
    ai_request_timeout: int = Field(default=120, ge=5, le=600)
    ai_max_tool_iterations: int = Field(default=5, ge=1, le=10)
    ai_max_conversation_messages: int = Field(default=12, ge=2, le=50)
    ai_max_tool_result_records: int = Field(default=50, ge=1, le=200)

    ai_enable_thinking: bool = Field(default=False)

    @classmethod
    def load(cls, env_file: Path | None = None) -> "AISettings":
        """Load AI configuration from environment variables and .env file."""
        root = find_project_root()
        target_env = env_file or (root / ".env")
        if target_env.is_file():
            load_dotenv(target_env, override=False)

        raw_enabled = os.environ.get("AI_ENABLED", "true").lower() in ("1", "true", "yes", "on")
        raw_provider = os.environ.get("AI_PROVIDER", "huggingface").lower()
        if raw_provider not in ("huggingface", "huggingface_endpoint", "local"):
            raw_provider = "huggingface"

        raw_thinking = os.environ.get("AI_ENABLE_THINKING", "false").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

        hf_prov = os.environ.get("HF_INFERENCE_PROVIDER")
        hf_token = os.environ.get("HF_TOKEN")
        hf_url = os.environ.get("HF_ENDPOINT_URL")

        try:
            return cls(
                ai_enabled=raw_enabled,
                ai_provider=raw_provider,  # type: ignore[arg-type]
                ai_model_id=os.environ.get("AI_MODEL_ID", "Qwen/Qwen3.5-4B"),
                hf_token=hf_token if hf_token else None,
                hf_inference_provider=hf_prov if hf_prov else None,
                hf_endpoint_url=hf_url if hf_url else None,
                ai_temperature=float(os.environ.get("AI_TEMPERATURE", "0.2")),
                ai_max_new_tokens=int(os.environ.get("AI_MAX_NEW_TOKENS", "2048")),
                ai_request_timeout=int(os.environ.get("AI_REQUEST_TIMEOUT", "120")),
                ai_max_tool_iterations=int(os.environ.get("AI_MAX_TOOL_ITERATIONS", "5")),
                ai_max_conversation_messages=int(
                    os.environ.get("AI_MAX_CONVERSATION_MESSAGES", "12")
                ),
                ai_enable_thinking=raw_thinking,
            )
        except Exception as e:
            raise AIConfigurationError(f"Failed to validate AI configuration: {e}") from e

    def validate_provider_requirements(self) -> None:
        """Validate prerequisites for the selected AI provider."""
        if not self.ai_enabled:
            return

        if self.ai_provider == "huggingface_endpoint":
            if not self.hf_endpoint_url:
                raise AIConfigurationError(
                    "HF_ENDPOINT_URL is required when AI_PROVIDER is set to 'huggingface_endpoint'."
                )

        if self.ai_provider == "huggingface":
            # hf_token is recommended for serverless Inference Providers
            pass


@lru_cache(maxsize=1)
def get_ai_settings() -> AISettings:
    """Return cached AI subsystem settings."""
    settings = AISettings.load()
    settings.validate_provider_requirements()
    return settings
