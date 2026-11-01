"""Mode B — Dedicated Hugging Face Inference Endpoints client (vLLM/TGI/SGLang)."""

import time
from collections.abc import Sequence

from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError

from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.exceptions import (
    AuthenticationError,
    EndpointUnavailableError,
    RateLimitError,
    RequestTimeoutError,
)
from election_research.ai.provider import AIProvider
from election_research.ai.response_parser import parse_model_response
from election_research.ai.schemas import ChatMessage, ModelResponse, ProviderHealth, ToolDefinition
from election_research.core.logging import get_logger
from election_research.core.security import redact_sensitive_text

logger = get_logger(__name__)


class HuggingFaceEndpointProvider(AIProvider):
    """Client for dedicated Hugging Face Inference Endpoints hosting Qwen3.5-4B."""

    def __init__(self, settings: AISettings | None = None) -> None:
        self.settings = settings or get_ai_settings()
        self._client: InferenceClient | None = None

    @property
    def provider_id(self) -> str:
        return "huggingface_endpoint"

    @property
    def model_id(self) -> str:
        return self.settings.ai_model_id

    def _get_client(self) -> InferenceClient:
        if self._client is None:
            if not self.settings.hf_endpoint_url:
                raise EndpointUnavailableError(
                    "HF_ENDPOINT_URL não configurado para o provedor 'huggingface_endpoint'."
                )
            self._client = InferenceClient(
                base_url=self.settings.hf_endpoint_url,
                token=self.settings.hf_token,
                timeout=self.settings.ai_request_timeout,
            )
        return self._client

    def generate_response(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition] | None = None,
    ) -> ModelResponse:
        """Send chat completion request to dedicated Hugging Face endpoint."""
        client = self._get_client()
        start_time = time.perf_counter()

        formatted_messages = [m.to_dict() for m in messages]
        formatted_tools = [t.to_hf_tool() for t in tools] if tools else None

        kwargs: dict = {
            "messages": formatted_messages,
            "max_tokens": self.settings.ai_max_new_tokens,
            "temperature": self.settings.ai_temperature,
        }
        if formatted_tools:
            kwargs["tools"] = formatted_tools

        try:
            resp = client.chat_completion(**kwargs)
            duration = time.perf_counter() - start_time

            choice = resp.choices[0]
            message = choice.message
            raw_content = message.content or ""
            native_tools = getattr(message, "tool_calls", None)

            token_usage = None
            if hasattr(resp, "usage") and resp.usage:
                token_usage = {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", 0),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", 0),
                    "total_tokens": getattr(resp.usage, "total_tokens", 0),
                }

            return parse_model_response(
                raw_content=raw_content,
                native_tool_calls=native_tools,
                duration_seconds=duration,
                token_usage=token_usage,
            )

        except HfHubHTTPError as e:
            sanitized = redact_sensitive_text(str(e))
            status_code = getattr(e.response, "status_code", 500) if hasattr(e, "response") else 500

            if status_code in (401, 403):
                raise AuthenticationError(
                    f"Endpoint authentication failed (HTTP {status_code}): {sanitized}"
                ) from e
            if status_code == 429:
                raise RateLimitError(f"Endpoint rate limit reached: {sanitized}") from e
            if status_code in (502, 503, 504):
                raise EndpointUnavailableError(
                    f"Endpoint offline or initializing (HTTP {status_code}): {sanitized}"
                ) from e

            raise EndpointUnavailableError(
                f"Endpoint request failed (HTTP {status_code}): {sanitized}"
            ) from e

        except TimeoutError as e:
            raise RequestTimeoutError(
                f"Endpoint timed out after {self.settings.ai_request_timeout}s"
            ) from e
        except Exception as e:
            sanitized = redact_sensitive_text(str(e))
            if "timeout" in sanitized.lower():
                raise RequestTimeoutError(f"Endpoint timed out: {sanitized}") from e
            raise EndpointUnavailableError(f"Endpoint request error: {sanitized}") from e

    def health_check(self) -> ProviderHealth:
        """Smoke test for dedicated endpoint deployment."""
        start_time = time.perf_counter()
        if not self.settings.hf_endpoint_url:
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                is_available=False,
                status_message="HF_ENDPOINT_URL não configurado.",
                latency_ms=0.0,
                supports_tools=False,
            )

        try:
            client = self._get_client()
            client.chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            latency = (time.perf_counter() - start_time) * 1000.0
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                is_available=True,
                status_message=f"Endpoint dedicado ativo ({latency:.0f}ms).",
                latency_ms=latency,
                supports_tools=True,
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000.0
            sanitized = redact_sensitive_text(str(e))
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                is_available=False,
                status_message=f"Endpoint inacessível: {sanitized}",
                latency_ms=latency,
                supports_tools=False,
            )
