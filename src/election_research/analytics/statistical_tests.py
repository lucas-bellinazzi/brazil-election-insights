"""Statistical testing and distribution metrics for electoral datasets."""

from typing import Any

import numpy as np
import polars as pl
from scipy import stats

from election_research.core.exceptions import AnalyticsError


def compute_distribution_summary(series: pl.Series) -> dict[str, float]:
    """Calculate central tendency, dispersion, and shape parameters for a metric."""
    arr = series.drop_nulls().to_numpy()
    if len(arr) == 0:
        return {}

    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0
    median = float(np.median(arr))
    q25 = float(np.percentile(arr, 25))
    q75 = float(np.percentile(arr, 75))
    iqr = q75 - q25

    skewness = float(stats.skew(arr)) if len(arr) > 2 else 0.0
    kurtosis = float(stats.kurtosis(arr)) if len(arr) > 3 else 0.0

    return {
        "count": float(len(arr)),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "median": round(median, 4),
        "q25": round(q25, 4),
        "q75": round(q75, 4),
        "iqr": round(iqr, 4),
        "skewness": round(skewness, 4),
        "kurtosis": round(kurtosis, 4),
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
    }


def compare_distributions_ks_test(series_a: pl.Series, series_b: pl.Series) -> dict[str, Any]:
    """Execute two-sample Kolmogorov-Smirnov test to compare two empirical distributions."""
    a = series_a.drop_nulls().to_numpy()
    b = series_b.drop_nulls().to_numpy()

    if len(a) < 5 or len(b) < 5:
        raise AnalyticsError("Both distributions require at least 5 observations for KS test.")

    res = stats.ks_2samp(a, b)
    return {
        "statistic": round(float(res.statistic), 4),
        "p_value": float(res.pvalue),
        "sample_a_size": len(a),
        "sample_b_size": len(b),
        "significant_at_05": bool(res.pvalue < 0.05),
    }


def compute_correlation(series_a: pl.Series, series_b: pl.Series) -> dict[str, float]:
    """Compute Pearson linear and Spearman rank correlation between two metrics."""
    df = pl.DataFrame({"a": series_a, "b": series_b}).drop_nulls()
    if len(df) < 5:
        raise AnalyticsError("At least 5 paired observations required for correlation.")

    arr_a = df["a"].to_numpy()
    arr_b = df["b"].to_numpy()

    p_corr, p_val = stats.pearsonr(arr_a, arr_b)
    s_corr, s_val = stats.spearmanr(arr_a, arr_b)

    return {
        "pearson_r": round(float(p_corr), 4),
        "pearson_p_value": float(p_val),
        "spearman_rho": round(float(s_corr), 4),
        "spearman_p_value": float(s_val),
    }
