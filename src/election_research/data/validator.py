"""Data validation rules and integrity constraints for Silver datasets."""

from dataclasses import dataclass

import polars as pl

from election_research.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class ValidationReport:
    """Summary of data validation outcome."""

    total_records: int
    valid_records: int
    rejected_records: int
    rejection_reasons: dict[str, int]


def validate_silver_data(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, ValidationReport]:
    """Validate normalized dataframe against domain rules and referential constraints.

    Returns:
        tuple of (valid_dataframe, rejected_dataframe, validation_report)
    """
    total_records = len(df)
    if total_records == 0:
        report = ValidationReport(0, 0, 0, {})
        return df, df, report

    # 1. Mandatory key presence
    mandatory_cols = [
        "state_abbreviation",
        "municipality_tse_code",
        "electoral_zone",
        "polling_section",
        "office_code",
        "ballot_number",
        "vote_count",
    ]
    missing_key_cond = pl.any_horizontal(
        [pl.col(c).is_null() for c in mandatory_cols if c in df.columns]
    )

    # 2. Non-negative counts
    negative_counts_cond = (
        (pl.col("vote_count") < 0)
        | (pl.col("eligible_voters") < 0)
        | (pl.col("actual_turnout") < 0)
        | (pl.col("abstentions") < 0)
    )

    # 3. Turnout balance identity (aptos == comparecimento + abstencoes)
    turnout_balance_cond = pl.col("eligible_voters") != (
        pl.col("actual_turnout") + pl.col("abstentions")
    )

    # Label rejection reasons
    rejection_expr = (
        pl.when(missing_key_cond)
        .then(pl.lit("MISSING_MANDATORY_KEYS"))
        .when(negative_counts_cond)
        .then(pl.lit("NEGATIVE_COUNTS"))
        .when(turnout_balance_cond)
        .then(pl.lit("TURNOUT_BALANCE_MISMATCH"))
        .otherwise(None)
        .alias("rejection_reason")
    )

    evaluated_df = df.with_columns(rejection_expr)

    valid_df = evaluated_df.filter(pl.col("rejection_reason").is_null()).drop("rejection_reason")
    rejected_df = evaluated_df.filter(pl.col("rejection_reason").is_not_null())

    reasons_count: dict[str, int] = {}
    if len(rejected_df) > 0:
        counts = rejected_df["rejection_reason"].value_counts().to_dicts()
        reasons_count = {row["rejection_reason"]: row["count"] for row in counts}
        logger.warning(
            "Validation identified %d rejected record(s): %s",
            len(rejected_df),
            reasons_count,
        )

    report = ValidationReport(
        total_records=total_records,
        valid_records=len(valid_df),
        rejected_records=len(rejected_df),
        rejection_reasons=reasons_count,
    )

    return valid_df, rejected_df, report
