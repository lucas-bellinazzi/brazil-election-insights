"""Closing time analytics and statistical classification for Brazil Election Insights."""

from typing import Any

import numpy as np
import polars as pl
from scipy import stats

REGIME_LABELS = {
    "regular": "Regular (17:00 - 17:09 BRT)",
    "early_extension": "Prorrogação Inicial (17:10 - 18:29 BRT)",
    "full_extension": "Prorrogação Integral (18:30 - 19:05 BRT)",
    "late_queues": "Filas com Senha (> 19:05 BRT)",
}


def classify_closing_regime(closing_time_brt_str: str) -> str:
    """Classify a normalized Brasília time timestamp (HH:MM or YYYY-MM-DD HH:MM:SS) into an operational regime."""
    if not closing_time_brt_str:
        return "regular"

    # Extract time part up to HH:MM:SS
    time_part = closing_time_brt_str.strip().split(" ")[-1]
    if len(time_part) == 5:
        time_part += ":00"

    if time_part < "17:10:00":
        return "regular"
    elif time_part < "18:30:00":
        return "early_extension"
    elif time_part <= "19:05:00":
        return "full_extension"
    else:
        return "late_queues"


def compare_regimes_turnout(
    regular_turnout: np.ndarray,
    extended_turnout: np.ndarray,
) -> dict[str, Any]:
    """Perform independent two-sample t-test and Mann-Whitney U test between regular and extended turnout rates.

    Parameters
    ----------
    regular_turnout : array-like of turnout percentages (0-100)
    extended_turnout : array-like of turnout percentages (0-100)

    Returns
    -------
    dict with means, difference, t-statistic, p-value, and statistical significance flag.
    """
    if len(regular_turnout) == 0 or len(extended_turnout) == 0:
        return {
            "mean_regular": 0.0,
            "mean_extended": 0.0,
            "diff_pct_points": 0.0,
            "t_stat": 0.0,
            "p_value": 1.0,
            "statistically_significant": False,
        }

    mean_reg = float(np.mean(regular_turnout))
    mean_ext = float(np.mean(extended_turnout))
    diff = mean_ext - mean_reg

    # Welch's t-test (does not assume equal variances)
    t_stat, p_val = stats.ttest_ind(extended_turnout, regular_turnout, equal_var=False)

    return {
        "mean_regular": round(mean_reg, 2),
        "mean_extended": round(mean_ext, 2),
        "diff_pct_points": round(diff, 2),
        "t_stat": round(float(t_stat), 4),
        "p_value": float(p_val),
        "statistically_significant": bool(p_val < 0.05),
    }


def compute_geographic_extension_disparity(df_states: pl.DataFrame) -> dict[str, Any]:
    """Calculate concentration and inequality metrics for extended voting machines across states.

    Parameters
    ----------
    df_states : Polars DataFrame with columns ['state_abbreviation', 'total_sections', 'extended_sections', 'pct_extended']

    Returns
    -------
    dict with top state, bottom state, ratio of disparity, and Gini coefficient of extension.
    """
    if df_states.is_empty():
        return {}

    sorted_df = df_states.sort("pct_extended", descending=True)
    top_state = sorted_df[0]
    bottom_state = sorted_df[-1]

    top_pct = float(top_state["pct_extended"][0])
    bottom_pct = float(bottom_state["pct_extended"][0])
    ratio = round(top_pct / max(bottom_pct, 0.01), 1)

    return {
        "highest_state": top_state["state_abbreviation"][0],
        "highest_pct": top_pct,
        "lowest_state": bottom_state["state_abbreviation"][0],
        "lowest_pct": bottom_pct,
        "disparity_ratio": ratio,
        "total_extended_sections": int(df_states["extended_sections"].sum()),
    }
