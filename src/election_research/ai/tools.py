"""Public facade and backward-compatible exports for analytical AI tools."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from election_research.ai.schemas import ToolCall, ToolDefinition, ToolResult
from election_research.ai.tool_executor import ToolExecutor
from election_research.ai.tool_registry import (
    ToolRegistry,
)
from election_research.core.security import sanitize_uf


# Compatibility argument classes for legacy tests and security validation
class StandardElectionArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    year: int = Field(default=2026, ge=1988, le=2100)
    election_round: int = Field(default=2, ge=1, le=2)
    office_code: int = Field(default=1, ge=1, le=13)


class TopAbstentionToolArgs(StandardElectionArgs):
    min_voters: int = Field(default=5000, ge=0, le=100_000_000)
    top_n: int = Field(default=10, ge=1, le=100)


class MunicipalityToolArgs(StandardElectionArgs):
    municipality_name: str = Field(default="", max_length=150)
    uf: str | None = Field(default=None, max_length=2)

    @field_validator("uf")
    @classmethod
    def check_uf(cls, v: str | None) -> str | None:
        return sanitize_uf(v) if v else None


_DEFAULT_REGISTRY = ToolRegistry()
_DEFAULT_EXECUTOR = ToolExecutor(registry=_DEFAULT_REGISTRY)

TOOL_DEFINITIONS: list[dict[str, Any]] = [t.to_hf_tool() for t in _DEFAULT_REGISTRY.list_tools()]

# Legacy alias mappings for seamless backward compatibility
LEGACY_TOOL_ALIASES = {
    "get_election_overview": "get_national_summary",
    "get_candidate_rankings": "get_candidate_results",
    "get_top_abstention_municipalities": "get_abstention_analysis",
    "get_state_results": "get_state_summary",
    "get_municipality_result": "get_municipality_summary",
}


def get_tool_definitions() -> list[ToolDefinition]:
    """Return all available tool definitions for Qwen3.5-4B."""
    return _DEFAULT_REGISTRY.list_tools()


def execute_tool_call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Backward-compatible function executing tool call and returning dict payload."""
    canonical_name = LEGACY_TOOL_ALIASES.get(tool_name, tool_name)
    # Map legacy argument keys if present
    mapped_args = dict(arguments)
    if "year" in mapped_args and "election_year" not in mapped_args:
        mapped_args["election_year"] = mapped_args.pop("year")
    if (
        "uf" in mapped_args
        and "state_code" not in mapped_args
        and canonical_name == "get_state_summary"
    ):
        mapped_args["state_code"] = mapped_args.pop("uf")
    if "name" in mapped_args and "municipality_code" not in mapped_args:
        mapped_args["municipality_code"] = mapped_args.pop("name")
    if "municipality_name" in mapped_args and "municipality_code" not in mapped_args:
        mapped_args["municipality_code"] = mapped_args.pop("municipality_name")

    call = ToolCall(id="call_legacy", name=canonical_name, arguments=mapped_args)
    result: ToolResult = _DEFAULT_EXECUTOR.execute(call)
    if result.success:
        if isinstance(result.data, dict):
            # Return data directly at top level for compatibility with older tests
            merged = dict(result.data)
            merged["provenance"] = result.provenance
            return merged
        if isinstance(result.data, list):
            # If list of candidates
            if canonical_name == "get_candidate_results":
                return {"candidates": result.data, "provenance": result.provenance}
            if canonical_name in ("get_state_summary", "compare_geographic_results"):
                return {"states": result.data, "provenance": result.provenance}
            return {"items": result.data, "provenance": result.provenance}
        return {"data": result.data, "provenance": result.provenance}
    return {"error": result.error}
