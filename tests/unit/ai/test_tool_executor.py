"""Unit tests for tool executor operations and schema validation."""

from election_research.ai.schemas import ToolCall
from election_research.ai.tool_executor import ToolExecutor


def test_executor_national_summary():
    executor = ToolExecutor()
    call = ToolCall(
        id="call_nat",
        name="get_national_summary",
        arguments={"election_year": 2026, "election_round": 2},
    )
    res = executor.execute(call)
    assert res.success is True
    assert res.data is not None
    assert "total_eligible_voters" in res.data
    assert res.provenance["layer"] == "Gold - gold_national_summary"


def test_executor_invalid_state_code():
    executor = ToolExecutor()
    call = ToolCall(
        id="call_st",
        name="get_state_summary",
        arguments={"state_code": "INVALID_STATE", "election_year": 2026},
    )
    res = executor.execute(call)
    assert res.success is False
    assert "Argumentos inválidos" in res.error or "Invalid UF" in res.error


def test_executor_unauthorized_tool():
    executor = ToolExecutor()
    call = ToolCall(
        id="call_bad",
        name="execute_sql_dump",
        arguments={},
    )
    res = executor.execute(call)
    assert res.success is False
    assert "não permitida" in res.error


def test_executor_anomalies_detection():
    executor = ToolExecutor()
    call = ToolCall(
        id="call_anom",
        name="detect_statistical_anomalies",
        arguments={
            "geographic_identifier": "AC",
            "method": "zscore",
            "threshold": 3.0,
            "election_year": 2026,
            "election_round": 2,
        },
    )
    res = executor.execute(call)
    assert res.success is True
    assert "disclaimer" in res.provenance
    assert "fraude" in res.provenance["disclaimer"]
