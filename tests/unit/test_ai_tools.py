"""Unit tests for AI analytical tools and registry."""

from election_research.ai.tool_registry import ToolRegistry
from election_research.ai.tools import TOOL_DEFINITIONS, execute_tool_call


def test_tool_definitions_present():
    assert len(TOOL_DEFINITIONS) >= 8
    tool_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
    assert "get_national_summary" in tool_names
    assert "get_state_summary" in tool_names
    assert "get_municipality_summary" in tool_names
    assert "get_candidate_results" in tool_names
    assert "compare_geographic_results" in tool_names
    assert "get_abstention_analysis" in tool_names
    assert "detect_statistical_anomalies" in tool_names
    assert "get_polling_section_details" in tool_names


def test_execute_national_summary():
    res = execute_tool_call("get_national_summary", {"election_year": 2026, "election_round": 2})
    assert "total_eligible_voters" in res
    assert res["total_eligible_voters"] > 0
    assert "provenance" in res


def test_execute_candidate_results():
    res = execute_tool_call("get_candidate_results", {"election_year": 2026, "election_round": 2})
    assert "candidates" in res
    assert len(res["candidates"]) > 0


def test_execute_unknown_tool():
    res = execute_tool_call("unauthorized_eval", {})
    assert "error" in res


def test_registry_allowlist():
    registry = ToolRegistry()
    assert registry.is_tool_allowed("get_national_summary") is True
    assert registry.is_tool_allowed("execute_sql") is False
    assert registry.is_tool_allowed("run_python") is False
