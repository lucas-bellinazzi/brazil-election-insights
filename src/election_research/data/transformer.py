"""Transformation of validated data into dimensional and fact Silver Parquet tables."""

from pathlib import Path

import polars as pl

from election_research.core.exceptions import TransformationError
from election_research.core.logging import get_logger
from election_research.data.schemas import (
    CANDIDATES_COLUMNS,
    ELECTIONS_COLUMNS,
    POLLING_SECTIONS_COLUMNS,
    VOTES_COLUMNS,
)

logger = get_logger(__name__)


def transform_to_silver_tables(df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Split normalized, validated DataFrame into dimensional and fact tables."""
    try:
        # Elections dimensional table (distinct per round)
        elections_df = df.select([c for c in ELECTIONS_COLUMNS if c in df.columns]).unique()

        # Polling sections dimensional table (distinct per section)
        polling_sections_df = df.select(
            [c for c in POLLING_SECTIONS_COLUMNS if c in df.columns]
        ).unique(
            subset=[
                "election_year",
                "election_round",
                "state_abbreviation",
                "municipality_tse_code",
                "electoral_zone",
                "polling_section",
            ]
        )

        # Candidates dimensional table (distinct per candidate/vote option)
        candidates_df = df.select([c for c in CANDIDATES_COLUMNS if c in df.columns]).unique(
            subset=["election_year", "election_round", "office_code", "ballot_number"]
        )

        # Votes fact table
        votes_df = df.select([c for c in VOTES_COLUMNS if c in df.columns])

        return {
            "elections": elections_df,
            "polling_sections": polling_sections_df,
            "candidates": candidates_df,
            "votes": votes_df,
        }
    except Exception as e:
        raise TransformationError(f"Failed to transform data to silver tables: {e}") from e


def write_silver_parquet(
    silver_tables: dict[str, pl.DataFrame],
    silver_dir: Path,
    year: int,
    election_round: str,
    uf: str,
) -> dict[str, Path]:
    """Persist silver tables to partitioned Parquet files."""
    written_paths: dict[str, Path] = {}

    for table_name, df in silver_tables.items():
        table_dir = silver_dir / str(year) / table_name / f"round={election_round}"
        table_dir.mkdir(parents=True, exist_ok=True)
        file_path = table_dir / f"{table_name}_{uf}.parquet"

        # Write columnar parquet with snappy compression
        df.write_parquet(file_path, compression="snappy")
        written_paths[table_name] = file_path

    logger.debug(
        "Saved Silver Parquet tables for Year %d, Round %s, UF %s to %s",
        year,
        election_round,
        uf,
        silver_dir,
    )
    return written_paths
