"""Unit tests for response parsing and Qwen3.5 thinking tag extraction."""

from election_research.ai.response_parser import (
    extract_fallback_tool_calls,
    parse_model_response,
    strip_thinking_tags,
)


def test_strip_thinking_tags_present():
    raw = "<think>\nThinking through turn...\nNeed to query state SP.\n</think>\nO comparecimento em SP foi de 78%."
    clean, thinking = strip_thinking_tags(raw)
    assert clean == "O comparecimento em SP foi de 78%."
    assert thinking is not None
    assert "Need to query state SP" in thinking
    assert "<think>" not in clean


def test_strip_thinking_tags_absent():
    raw = "Resposta direta sem tags."
    clean, thinking = strip_thinking_tags(raw)
    assert clean == "Resposta direta sem tags."
    assert thinking is None


def test_extract_fallback_xml_tool_call():
    raw = 'Vou consultar o resumo nacional: <tool_call>{"name": "get_national_summary", "arguments": {"election_year": 2026}}</tool_call>'
    clean, calls = extract_fallback_tool_calls(raw)
    assert len(calls) == 1
    assert calls[0].name == "get_national_summary"
    assert calls[0].arguments == {"election_year": 2026}
    assert "<tool_call>" not in clean


def test_parse_model_response_with_native_tool_call():
    native_call = {
        "id": "call_123",
        "function": {
            "name": "get_state_summary",
            "arguments": '{"state_code": "SP"}',
        },
    }
    raw = "<think>Calling tool</think>Processando..."
    model_resp = parse_model_response(raw_content=raw, native_tool_calls=[native_call])
    assert model_resp.content == "Processando..."
    assert model_resp.thinking_content == "Calling tool"
    assert len(model_resp.tool_calls) == 1
    assert model_resp.tool_calls[0].name == "get_state_summary"
    assert model_resp.tool_calls[0].arguments == {"state_code": "SP"}
