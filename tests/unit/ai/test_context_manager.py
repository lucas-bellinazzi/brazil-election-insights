"""Unit tests for context window management and token budget bounding."""

from election_research.ai.config import AISettings
from election_research.ai.context_manager import ContextManager
from election_research.ai.schemas import ChatMessage, ToolResult


def test_context_manager_sliding_window():
    settings = AISettings(ai_max_conversation_messages=5)
    mgr = ContextManager(settings=settings)

    # 8 user/assistant history messages
    history = [
        ChatMessage(role="user", content=f"Msg {i}")
        if i % 2 == 0
        else ChatMessage(role="assistant", content=f"Ans {i}")
        for i in range(8)
    ]

    messages = mgr.build_prompt_messages(history=history, current_user_message="Current")
    # Must have System Prompt at index 0, followed by at most (5 - 1) trimmed messages + current user message
    assert messages[0].role == "system"
    assert len(messages) <= 6
    assert messages[-1].content == "Current"


def test_format_tool_result_content_truncation():
    settings = AISettings(ai_max_tool_result_records=10)
    mgr = ContextManager(settings=settings)

    large_data = [{"idx": i} for i in range(50)]
    res = ToolResult(
        tool_name="test_tool",
        arguments={},
        success=True,
        data=large_data,
        record_count=50,
    )

    formatted = mgr.format_tool_result_content(res)
    assert "truncation_notice" in formatted
    assert "Mostrando 10 de 50" in formatted
