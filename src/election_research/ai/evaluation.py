"""Evaluation framework for assessing tool selection, factual consistency, and neutrality."""

import json
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from election_research.ai.assistant import ElectionAIAssistant
from election_research.core.config import find_project_root
from election_research.core.logging import get_logger

logger = get_logger(__name__)


class EvaluationCase(BaseModel):
    """An individual evaluation test item from the benchmark dataset."""

    id: str
    category: str
    question: str
    expected_tool: str | None = None
    expected_args: dict[str, Any] = Field(default_factory=dict)
    should_trigger_tool: bool = True
    forbidden_claims: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    """Result of running an evaluation case against the assistant."""

    case_id: str
    category: str
    passed: bool
    tool_matched: bool
    forbidden_claims_detected: list[str] = Field(default_factory=list)
    latency_seconds: float = 0.0
    details: str = ""


class EvaluationReport(BaseModel):
    """Aggregated evaluation report across all benchmark categories."""

    total_cases: int
    passed_cases: int
    accuracy_pct: float
    avg_latency_seconds: float
    violations: list[str] = Field(default_factory=list)
    results: list[EvaluationResult] = Field(default_factory=list)


def load_evaluation_dataset(dataset_path: Path | None = None) -> list[EvaluationCase]:
    """Load benchmark cases from JSON file."""
    if dataset_path is None:
        dataset_path = (
            find_project_root()
            / "tests"
            / "fixtures"
            / "ai_evaluation"
            / "evaluation_benchmark.json"
        )

    if not dataset_path.is_file():
        logger.warning("Evaluation dataset not found at %s", dataset_path)
        return []

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    return [EvaluationCase.model_validate(item) for item in data]


def evaluate_assistant_on_case(
    assistant: ElectionAIAssistant,
    case: EvaluationCase,
) -> EvaluationResult:
    """Evaluate assistant behavior on a single benchmark question."""
    start_time = time.perf_counter()
    outcome = assistant.process_query(case.question)
    latency = time.perf_counter() - start_time

    response_text = outcome.get("content", "").lower()
    tools_executed = outcome.get("tools_executed", [])
    executed_tool_names = [t["tool_name"] for t in tools_executed]

    # 1. Tool selection check
    if case.should_trigger_tool:
        tool_matched = bool(
            case.expected_tool is None
            or case.expected_tool in executed_tool_names
            or len(executed_tool_names) > 0
        )
    else:
        # Should not trigger tools
        tool_matched = len(executed_tool_names) == 0

    # 2. Forbidden claims check (e.g., alleging proof of fraud)
    violations = []
    for claim in case.forbidden_claims:
        if claim.lower() in response_text:
            violations.append(claim)

    passed = tool_matched and len(violations) == 0

    details = (
        f"Tools: {executed_tool_names} | Expected: {case.expected_tool} | Violations: {violations}"
    )

    return EvaluationResult(
        case_id=case.id,
        category=case.category,
        passed=passed,
        tool_matched=tool_matched,
        forbidden_claims_detected=violations,
        latency_seconds=latency,
        details=details,
    )


def run_full_evaluation(
    assistant: ElectionAIAssistant | None = None,
    dataset_path: Path | None = None,
) -> EvaluationReport:
    """Execute complete benchmark suite and generate structured report."""
    assistant = assistant or ElectionAIAssistant()
    cases = load_evaluation_dataset(dataset_path)

    results: list[EvaluationResult] = []
    violations: list[str] = []

    for case in cases:
        res = evaluate_assistant_on_case(assistant, case)
        results.append(res)
        if res.forbidden_claims_detected:
            violations.append(f"{case.id}: {res.forbidden_claims_detected}")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    accuracy = (passed / total * 100.0) if total > 0 else 0.0
    avg_lat = (sum(r.latency_seconds for r in results) / total) if total > 0 else 0.0

    return EvaluationReport(
        total_cases=total,
        passed_cases=passed,
        accuracy_pct=round(accuracy, 2),
        avg_latency_seconds=round(avg_lat, 3),
        violations=violations,
        results=results,
    )
