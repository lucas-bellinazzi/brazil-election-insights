"""Unit tests for anomaly detection algorithms."""

import polars as pl

from election_research.analytics.anomalies import (
    NEUTRAL_DISCLAIMER,
    detect_anomalies_iqr,
    detect_anomalies_isolation_forest,
    detect_anomalies_zscore,
)


def test_detect_anomalies_zscore():
    # 20 regular items with values ~20, one extreme outlier with value 95
    vals = [20.0 + (i % 3) for i in range(25)] + [95.0]
    df = pl.DataFrame({"municipality_name": [f"Muni_{i}" for i in range(26)], "metric": vals})

    flagged = detect_anomalies_zscore(df, metric_col="metric", threshold=2.5)
    assert len(flagged) >= 1
    assert "Muni_25" in flagged["municipality_name"].to_list()
    assert flagged["methodological_note"][0] == NEUTRAL_DISCLAIMER


def test_detect_anomalies_iqr():
    vals = [10.0 + (i % 2) for i in range(25)] + [80.0]
    df = pl.DataFrame({"municipality_name": [f"Muni_{i}" for i in range(26)], "metric": vals})

    flagged = detect_anomalies_iqr(df, metric_col="metric", factor=1.5)
    assert len(flagged) >= 1
    assert "Muni_25" in flagged["municipality_name"].to_list()


def test_detect_anomalies_isolation_forest():
    features_a = [10.0 + (i % 2) for i in range(30)] + [90.0]
    features_b = [5.0 + (i % 3) for i in range(30)] + [85.0]
    df = pl.DataFrame({"feat_a": features_a, "feat_b": features_b})

    flagged = detect_anomalies_isolation_forest(
        df, feature_cols=["feat_a", "feat_b"], contamination=0.05
    )
    assert len(flagged) >= 1
    assert "anomaly_score" in flagged.columns
