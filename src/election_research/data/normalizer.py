"""Data normalization from raw TSE CSV representations to Silver canonical structures."""

from pathlib import Path

import polars as pl

from election_research.core.exceptions import TransformationError
from election_research.core.logging import get_logger
from election_research.data.schemas import SILVER_CANONICAL_DTYPES, TSE_TO_CANONICAL_COLUMNS

logger = get_logger(__name__)


def normalize_bu_dataframe(df: pl.DataFrame, source_file: str | Path) -> pl.DataFrame:
    """Transform raw TSE DataFrame into normalized, typed canonical representation."""
    source_name = Path(source_file).name

    # 1. Check and rename columns
    rename_map = {
        col: TSE_TO_CANONICAL_COLUMNS[col] for col in df.columns if col in TSE_TO_CANONICAL_COLUMNS
    }
    df = df.rename(rename_map)

    # 2. Add source_file for data provenance
    df = df.with_columns(pl.lit(source_name).alias("source_file"))

    # 3. Clean string columns and replace sentinels with NULL
    exprs: list[pl.Expr] = []
    for col_name, dtype in SILVER_CANONICAL_DTYPES.items():
        if col_name not in df.columns:
            continue

        col_expr = pl.col(col_name)

        if dtype == pl.Utf8:
            # Strip spaces, quotes, and convert "#NULO#" to null
            col_expr = col_expr.cast(pl.Utf8).str.strip_chars().str.strip_chars('"')
            col_expr = (
                pl.when(col_expr.is_in(["#NULO#", "", "None"]))
                .then(None)
                .otherwise(col_expr)
                .alias(col_name)
            )
        elif dtype in (pl.Int32, pl.Int64):
            # If currently string, clean sentinels before casting
            if df.schema[col_name] == pl.Utf8:
                col_expr = col_expr.str.strip_chars().str.strip_chars('"')
                col_expr = (
                    pl.when(col_expr.is_in(["#NULO#", "", "-1", "-3"]))
                    .then(None)
                    .otherwise(col_expr)
                    .cast(dtype, strict=False)
                    .alias(col_name)
                )
            else:
                if col_name in ("party_number", "electoral_board_number", "electoral_panel_number"):
                    col_expr = (
                        pl.when(col_expr.is_in([-1, -3]))
                        .then(None)
                        .otherwise(col_expr)
                        .cast(dtype)
                        .alias(col_name)
                    )
                else:
                    col_expr = col_expr.cast(dtype, strict=False).alias(col_name)

        exprs.append(col_expr)

    try:
        normalized_df = df.with_columns(exprs)
    except Exception as e:
        raise TransformationError(f"Failed to normalize dataframe for {source_name}: {e}") from e

    return normalized_df
