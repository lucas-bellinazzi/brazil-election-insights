"""Integration tests for the ElectionAIAssistant tool-calling loop using mocked provider responses."""

from election_research.ai.assistant import ElectionAIAssistant
from election_research.ai.config import AISettings
from election_research.ai.provider import AIProvider
from election_research.ai.schemas import ModelResponse, ProviderHealth, ToolCall


class MockedInferenceProvider(AIProvider):
    """Mocked inference provider simulating multi-turn Qwen3.5 tool-calling."""

    def __init__(self, step_responses: list[ModelResponse]) -> None:
        self.step_responses = list(step_responses)
        self.call_count = 0

    @property
    def provider_id(self) -> str:
        return "mock_huggingface"

    @property
    def model_id(self) -> str:
        return "Qwen/Qwen3.5-4B"

    def generate_response(self, messages, tools=None):
        idx = min(self.call_count, len(self.step_responses) - 1)
        resp = self.step_responses[idx]
        self.call_count += 1
        return resp

    def health_check(self):
        return ProviderHealth(
            provider_id="mock_huggingface",
            model_id="Qwen/Qwen3.5-4B",
            is_available=True,
            status_message="Mock provider ready.",
            latency_ms=1.0,
            supports_tools=True,
        )


def test_assistant_multi_turn_tool_loop():
    # Step 1: Model requests get_national_summary
    step1_resp = ModelResponse(
        content="Vou consultar os dados oficiais consolidados.",
        tool_calls=[
            ToolCall(
                id="call_mock_01",
                name="get_national_summary",
                arguments={"election_year": 2026, "election_round": 2},
            )
        ],
        raw_content="<think>User asked for national summary.</think>Vou consultar os dados oficiais.",
        thinking_content="User asked for national summary.",
    )

    # Step 2: Model interprets result and gives final answer
    step2_resp = ModelResponse(
        content="Segundo os dados consolidados do TSE para 2026 (2º Turno), o comparecimento foi de 79.5% e a taxa de abstenção foi de 20.5%.",
        tool_calls=[],
        raw_content="Segundo os dados consolidados do TSE para 2026...",
    )

    mock_provider = MockedInferenceProvider([step1_resp, step2_resp])
    settings = AISettings(ai_enabled=True)
    assistant = ElectionAIAssistant(provider=mock_provider, settings=settings)

    result = assistant.process_query("Como foi a eleição presidencial de 2026 no Brasil?")

    assert result["content"] == step2_resp.content
    assert len(result["tools_executed"]) == 1
    assert result["tools_executed"][0]["tool_name"] == "get_national_summary"
    assert result["tools_executed"][0]["success"] is True
    assert result["provider"] == "mock_huggingface"
    assert result["model"] == "Qwen/Qwen3.5-4B"
    assert mock_provider.call_count == 2
