"""Unit tests for statistical distribution tests and metrics."""

import polars as pl

from election_research.analytics.statistical_tests import (
    compare_distributions_ks_test,
    compute_correlation,
    compute_distribution_summary,
)


def test_compute_distribution_summary():
    s = pl.Series("turnout", [70.0, 75.0, 80.0, 85.0, 90.0])
    summary = compute_distribution_summary(s)

    assert summary["count"] == 5.0
    assert summary["mean"] == 80.0
    assert summary["median"] == 80.0
    assert summary["min"] == 70.0
    assert summary["max"] == 90.0


def test_compare_distributions_ks_test():
    s_a = pl.Series("dist1", [10, 12, 11, 14, 13, 15, 12])
    s_b = pl.Series("dist2", [50, 52, 51, 54, 53, 55, 52])

    res = compare_distributions_ks_test(s_a, s_b)
    assert "statistic" in res
    assert "p_value" in res
    assert res["significant_at_05"] is True


def test_compute_correlation():
    s_x = pl.Series("x", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    s_y = pl.Series("y", [2.0, 4.0, 6.0, 8.0, 10.0, 12.0])

    res = compute_correlation(s_x, s_y)
    assert res["pearson_r"] == 1.0
    assert res["spearman_rho"] == 1.0
