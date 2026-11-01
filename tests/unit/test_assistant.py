"""Unit tests for ElectionAIAssistant and deterministic fallback."""

from election_research.ai.assistant import ElectionAIAssistant


def test_assistant_deterministic_fallback():
    assistant = ElectionAIAssistant()
    # Test abstention query fallback
    res = assistant.process_query("Quais municípios tiveram a maior taxa de abstenção?")
    assert "content" in res
    assert len(res["tools_executed"]) > 0
    assert res["tools_executed"][0]["tool_name"] in (
        "get_top_abstention_municipalities",
        "get_abstention_analysis",
    )

    # Test candidate ranking query fallback
    res_cand = assistant.process_query("Qual o ranking dos candidatos?")
    assert "content" in res_cand
    assert len(res_cand["tools_executed"]) > 0
    assert res_cand["tools_executed"][0]["tool_name"] in (
        "get_candidate_rankings",
        "get_candidate_results",
    )
