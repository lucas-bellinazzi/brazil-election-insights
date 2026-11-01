"""Unit tests for conversation state and turns."""

from election_research.ai.conversation import Conversation
from election_research.ai.schemas import ToolCall


def test_conversation_lifecycle():
    conv = Conversation()
    assert len(conv.get_messages()) == 0

    conv.add_user_message("Olá, qual foi o comparecimento?")
    assert len(conv.get_messages()) == 1
    assert conv.get_messages()[0].role == "user"

    call = ToolCall(id="call_1", name="get_national_summary", arguments={})
    conv.add_assistant_message("Vou consultar o resumo.", tool_calls=[call])
    assert len(conv.get_messages()) == 2
    assert conv.get_messages()[1].tool_calls[0].name == "get_national_summary"

    conv.add_tool_result("call_1", "get_national_summary", '{"valid_votes": 1000000}')
    assert len(conv.get_messages()) == 3
    assert conv.get_messages()[2].role == "tool"

    conv.clear()
    assert len(conv.get_messages()) == 0

