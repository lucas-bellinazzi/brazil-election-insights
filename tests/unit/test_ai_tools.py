"""Unit tests for AI allowlisted analytical tools."""

from election_research.ai.tools import TOOL_DEFINITIONS, execute_tool_call


def test_tool_definitions_present():
    assert len(TOOL_DEFINITIONS) >= 4
    tool_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "get_election_overview" in tool_names
    assert "get_candidate_rankings" in tool_names
    assert "get_state_results" in tool_names
    assert "get_top_abstention_municipalities" in tool_names


def test_execute_tool_call_overview():
    res = execute_tool_call("get_election_overview", {"year": 2026, "election_round": 2})
    assert "total_eligible_voters" in res
    assert res["total_eligible_voters"] > 0


def test_execute_tool_call_candidates():
    res = execute_tool_call(
        "get_candidate_rankings", {"year": 2026, "election_round": 2, "office_code": 1}
    )
    assert "candidates" in res
    assert len(res["candidates"]) > 0


def test_execute_unknown_tool():
    res = execute_tool_call("unauthorized_eval", {})
    assert "error" in res
