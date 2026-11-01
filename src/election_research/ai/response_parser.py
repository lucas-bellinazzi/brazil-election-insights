"""Response parser for Qwen3.5-4B outputs, reasoning tag removal, and tool call extraction."""

import json
import re
import uuid
from typing import Any

from election_research.ai.schemas import ModelResponse, ToolCall
from election_research.core.logging import get_logger

logger = get_logger(__name__)

# Regex pattern for Qwen3.5 thinking blocks: <think>...</think>
THINKING_PATTERN = re.compile(r"<think>(.*?)</think>", re.DOTALL | re.IGNORECASE)

# Fallback patterns for JSON or XML-style tool calls if provider does not support native function calling
TOOL_CALL_XML_PATTERN = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL | re.IGNORECASE)
JSON_CODE_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*(\{[^`]*\"tool\":[^`]*\})\s*```", re.DOTALL)


def strip_thinking_tags(text: str) -> tuple[str, str | None]:
    """Extract and remove <think>...</think> internal reasoning blocks from Qwen3.5 text."""
    if not text:
        return "", None

    thinking_matches = THINKING_PATTERN.findall(text)
    thinking_content = (
        "\n\n".join(m.strip() for m in thinking_matches) if thinking_matches else None
    )

    # Remove the tags and content from the visible text
    clean_text = THINKING_PATTERN.sub("", text).strip()
    return clean_text, thinking_content


def extract_fallback_tool_calls(text: str) -> tuple[str, list[ToolCall]]:
    """Inspect text for structured tool calls emitted in fallback formats when native calling is unavailable."""
    tool_calls: list[ToolCall] = []
    clean_text = text

    # 1. XML style: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    xml_matches = TOOL_CALL_XML_PATTERN.findall(text)
    for raw in xml_matches:
        try:
            parsed = json.loads(raw.strip())
            name = parsed.get("name") or parsed.get("tool")
            args = parsed.get("arguments") or parsed.get("args", {})
            if name:
                tool_calls.append(
                    ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=args)
                )
        except Exception as e:
            logger.debug("Failed to parse XML tool call: %s", e)

    if xml_matches:
        clean_text = TOOL_CALL_XML_PATTERN.sub("", clean_text).strip()

    # 2. Markdown json code block with "tool" key
    if not tool_calls:
        json_matches = JSON_CODE_BLOCK_PATTERN.findall(text)
        for raw in json_matches:
            try:
                parsed = json.loads(raw.strip())
                name = parsed.get("tool") or parsed.get("name")
                args = parsed.get("arguments") or parsed.get("args", {})
                if name:
                    tool_calls.append(
                        ToolCall(id=f"call_{uuid.uuid4().hex[:8]}", name=name, arguments=args)
                    )
            except Exception as e:
                logger.debug("Failed to parse JSON block tool call: %s", e)

        if json_matches:
            clean_text = JSON_CODE_BLOCK_PATTERN.sub("", clean_text).strip()

    return clean_text, tool_calls


def parse_model_response(
    raw_content: str,
    native_tool_calls: list[Any] | None = None,
    duration_seconds: float = 0.0,
    token_usage: dict[str, int] | None = None,
) -> ModelResponse:
    """Parse raw model response, strip thinking tokens, and extract tool calls."""
    if raw_content is None:
        raw_content = ""

    clean_text, thinking = strip_thinking_tags(raw_content)

    tool_calls: list[ToolCall] = []

    # 1. First prioritize native tool calls returned by InferenceClient
    if native_tool_calls:
        for tc in native_tool_calls:
            try:
                # tc may be dict or HF ToolCall object
                if isinstance(tc, dict):
                    call_id = tc.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                    fn = tc.get("function", {})
                    fn_name = fn.get("name") or tc.get("name", "")
                    fn_args = fn.get("arguments", {})
                    if isinstance(fn_args, str):
                        fn_args = json.loads(fn_args)
                else:
                    # Huggingface ChatCompletionMessageToolCall object
                    call_id = getattr(tc, "id", f"call_{uuid.uuid4().hex[:8]}")
                    fn = getattr(tc, "function", None)
                    fn_name = getattr(fn, "name", "")
                    raw_args = getattr(fn, "arguments", {})
                    fn_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args

                if fn_name:
                    tool_calls.append(ToolCall(id=str(call_id), name=fn_name, arguments=fn_args))
            except Exception as e:
                logger.warning("Error parsing native tool call %s: %s", tc, e)

    # 2. If no native tool calls, inspect clean_text for fallback representations
    if not tool_calls and clean_text:
        clean_text, fallback_calls = extract_fallback_tool_calls(clean_text)
        if fallback_calls:
            tool_calls.extend(fallback_calls)

    return ModelResponse(
        content=clean_text,
        tool_calls=tool_calls,
        raw_content=raw_content,
        thinking_content=thinking,
        token_usage=token_usage,
        duration_seconds=duration_seconds,
    )
