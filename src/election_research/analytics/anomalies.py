"""Anomaly detection routines and statistical outlier signals for electoral investigation."""

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import polars as pl
from sklearn.ensemble import IsolationForest

from election_research.core.logging import get_logger

logger = get_logger(__name__)

NEUTRAL_DISCLAIMER = (
    "Sinal estatístico atípico identificado para investigação empírica e metodológica. "
    "Desvios estatísticos não constituem evidência ou prova de fraude ou manipulação eleitoral."
)


@dataclass(frozen=True)
class AnomalySignal:
    """Structured record of an identified statistical outlier signal."""

    unit_identifier: str
    unit_name: str
    metric_name: str
    observed_value: float
    reference_value: float
    method: str
    score: float
    threshold: float
    context: dict[str, Any]
    interpretation: str = NEUTRAL_DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_anomalies_zscore(
    df: pl.DataFrame,
    metric_col: str,
    id_col: str = "municipality_name",
    threshold: float = 3.0,
) -> pl.DataFrame:
    """Identify statistical anomalies using parametric Z-score standard deviation."""
    vals = df[metric_col].to_numpy()
    valid_mask = ~np.isnan(vals)

    if np.sum(valid_mask) < 5:
        return df.filter(pl.lit(False))

    mean_val = float(np.mean(vals[valid_mask]))
    std_val = float(np.std(vals[valid_mask]))

    if std_val == 0.0:
        return df.filter(pl.lit(False))

    z_scores = (vals - mean_val) / std_val
    abs_z = np.abs(z_scores)

    flagged_mask = abs_z >= threshold

    results_df = df.filter(pl.Series(flagged_mask)).with_columns(
        [
            pl.Series("anomaly_score", z_scores[flagged_mask]),
            pl.lit("Z-Score").alias("anomaly_method"),
            pl.lit(mean_val).alias("reference_mean"),
            pl.lit(threshold).alias("anomaly_threshold"),
            pl.lit(NEUTRAL_DISCLAIMER).alias("methodological_note"),
        ]
    )
    return results_df.sort("anomaly_score", descending=True)


def detect_anomalies_iqr(
    df: pl.DataFrame,
    metric_col: str,
    id_col: str = "municipality_name",
    factor: float = 1.5,
) -> pl.DataFrame:
    """Identify statistical anomalies using non-parametric Interquartile Range (IQR)."""
    vals = df[metric_col].to_numpy()
    valid_mask = ~np.isnan(vals)

    if np.sum(valid_mask) < 5:
        return df.filter(pl.lit(False))

    q25 = float(np.percentile(vals[valid_mask], 25))
    q75 = float(np.percentile(vals[valid_mask], 75))
    iqr = q75 - q25

    if iqr == 0.0:
        return df.filter(pl.lit(False))

    lower_bound = q25 - factor * iqr
    upper_bound = q75 + factor * iqr

    flagged_mask = (vals < lower_bound) | (vals > upper_bound)

    results_df = df.filter(pl.Series(flagged_mask)).with_columns(
        [
            pl.lit("IQR").alias("anomaly_method"),
            pl.lit(q25).alias("reference_q25"),
            pl.lit(q75).alias("reference_q75"),
            pl.lit(lower_bound).alias("lower_bound"),
            pl.lit(upper_bound).alias("upper_bound"),
            pl.lit(NEUTRAL_DISCLAIMER).alias("methodological_note"),
        ]
    )
    return results_df.sort(metric_col, descending=True)


def detect_anomalies_isolation_forest(
    df: pl.DataFrame,
    feature_cols: list[str],
    contamination: float = 0.01,
) -> pl.DataFrame:
    """Identify multi-dimensional anomalies using scikit-learn Isolation Forest."""
    if len(df) < 20:
        return df.filter(pl.lit(False))

    p_df = df.select(feature_cols).to_pandas().dropna()
    if len(p_df) < 20:
        return df.filter(pl.lit(False))

    clf = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    preds = clf.fit_predict(p_df)
    scores = clf.decision_function(p_df)

    anomaly_indices = np.where(preds == -1)[0]
    flagged_df = df[anomaly_indices].with_columns(
        [
            pl.Series("anomaly_score", scores[anomaly_indices]),
            pl.lit("IsolationForest").alias("anomaly_method"),
            pl.lit(NEUTRAL_DISCLAIMER).alias("methodological_note"),
        ]
    )
    return flagged_df.sort("anomaly_score", descending=False)
