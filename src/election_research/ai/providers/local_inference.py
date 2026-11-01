"""Mode C — Local development inference client (Local vLLM/SGLang server or Transformers)."""

import time
from collections.abc import Sequence
from typing import Any

from huggingface_hub import InferenceClient

from election_research.ai.config import AISettings, get_ai_settings
from election_research.ai.exceptions import (
    ModelUnavailableError,
    ProviderUnavailableError,
)
from election_research.ai.provider import AIProvider
from election_research.ai.response_parser import parse_model_response
from election_research.ai.schemas import ChatMessage, ModelResponse, ProviderHealth, ToolDefinition
from election_research.core.logging import get_logger
from election_research.core.security import redact_sensitive_text

logger = get_logger(__name__)


class LocalInferenceProvider(AIProvider):
    """Local inference provider communicating with local server (vLLM/SGLang) or direct transformers."""

    def __init__(self, settings: AISettings | None = None) -> None:
        self.settings = settings or get_ai_settings()
        self._local_server_url = self.settings.hf_endpoint_url or "http://localhost:8000/v1"
        self._client: InferenceClient | None = None
        self._pipeline: Any = None

    @property
    def provider_id(self) -> str:
        return "local"

    @property
    def model_id(self) -> str:
        return self.settings.ai_model_id

    def _get_server_client(self) -> InferenceClient:
        """Inference client connected to local OpenAI-compatible or vLLM server."""
        if self._client is None:
            self._client = InferenceClient(
                base_url=self._local_server_url,
                timeout=self.settings.ai_request_timeout,
            )
        return self._client

    def _init_local_transformers_pipeline(self) -> Any:
        """Lazily load PyTorch and Transformers if local server is not active."""
        if self._pipeline is not None:
            return self._pipeline

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

            logger.info("Initializing in-process Transformers pipeline for %s...", self.model_id)
            tokenizer = AutoTokenizer.from_pretrained(self.model_id)
            model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                torch_dtype="auto",
                device_map="auto" if torch.cuda.is_available() else "cpu",
            )
            self._pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
            return self._pipeline
        except ImportError as e:
            raise ProviderUnavailableError(
                "Local inference requires either a running server at http://localhost:8000/v1 "
                "or optional dependencies: `uv sync --extra local-ai` (torch, transformers, accelerate)."
            ) from e
        except Exception as e:
            raise ModelUnavailableError(f"Failed to load local model {self.model_id}: {e}") from e

    def generate_response(
        self,
        messages: Sequence[ChatMessage],
        tools: Sequence[ToolDefinition] | None = None,
    ) -> ModelResponse:
        """Execute chat completion via local server or fallback to in-process pipeline."""
        start_time = time.perf_counter()
        formatted_messages = [m.to_dict() for m in messages]
        formatted_tools = [t.to_hf_tool() for t in tools] if tools else None

        # Strategy 1: Attempt local inference server
        try:
            client = self._get_server_client()
            kwargs: dict = {
                "messages": formatted_messages,
                "max_tokens": self.settings.ai_max_new_tokens,
                "temperature": self.settings.ai_temperature,
            }
            if formatted_tools:
                kwargs["tools"] = formatted_tools

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

        except Exception as server_err:
            logger.debug(
                "Local server unavailable at %s, checking in-process pipeline: %s",
                self._local_server_url,
                server_err,
            )

        # Strategy 2: Attempt in-process Transformers
        try:
            pipe = self._init_local_transformers_pipeline()
            prompt = pipe.tokenizer.apply_chat_template(
                formatted_messages, tokenize=False, add_generation_prompt=True
            )
            out = pipe(
                prompt,
                max_new_tokens=self.settings.ai_max_new_tokens,
                temperature=self.settings.ai_temperature,
                do_sample=self.settings.ai_temperature > 0,
            )
            duration = time.perf_counter() - start_time
            generated = out[0]["generated_text"][len(prompt) :]

            return parse_model_response(
                raw_content=generated,
                duration_seconds=duration,
            )
        except Exception as e:
            sanitized = redact_sensitive_text(str(e))
            raise ProviderUnavailableError(
                f"Local inference failed (neither local server at {self._local_server_url} nor in-process pipeline available): {sanitized}"
            ) from e

    def health_check(self) -> ProviderHealth:
        """Check availability of local server or transformers libraries."""
        start_time = time.perf_counter()
        try:
            client = self._get_server_client()
            client.chat_completion(
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
            )
            latency = (time.perf_counter() - start_time) * 1000.0
            return ProviderHealth(
                provider_id=self.provider_id,
                model_id=self.model_id,
                is_available=True,
                status_message=f"Servidor local ativo em {self._local_server_url} ({latency:.0f}ms).",
                latency_ms=latency,
                supports_tools=True,
            )
        except Exception as e:
            # Check if transformers is available
            try:
                import torch
                import transformers

                return ProviderHealth(
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    is_available=True,
                    status_message=f"Ambiente local pronto com torch {torch.__version__} e transformers {transformers.__version__}.",
                    latency_ms=0.0,
                    supports_tools=False,
                )
            except ImportError:
                sanitized = redact_sensitive_text(str(e))
                return ProviderHealth(
                    provider_id=self.provider_id,
                    model_id=self.model_id,
                    is_available=False,
                    status_message=f"Servidor local offline ({sanitized}) e extras 'local-ai' não instalados.",
                    latency_ms=0.0,
                    supports_tools=False,
                )
