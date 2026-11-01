"""Unit tests for the evaluation dataset and benchmark runner."""

from election_research.ai.evaluation import (
    load_evaluation_dataset,
    run_full_evaluation,
)


def test_load_evaluation_dataset():
    cases = load_evaluation_dataset()
    assert len(cases) >= 10
    categories = {c.category for c in cases}
    assert "national_summary" in categories
    assert "state_comparison" in categories
    assert "abstention_analysis" in categories
    assert "statistical_anomalies" in categories
    assert "fraud_allegations" in categories


def test_run_full_evaluation():
    # Runs evaluation against deterministic fallback assistant
    report = run_full_evaluation()
    assert report.total_cases >= 10
    assert report.passed_cases > 0
    assert report.accuracy_pct > 0
    assert len(report.violations) == 0  # No unsupported fraud claims
