"""Descriptive electoral indicators and Gold layer aggregation logic."""

from pathlib import Path

import polars as pl

from election_research.core.logging import get_logger
from election_research.data.repository import DataRepository

logger = get_logger(__name__)


def compute_turnout_aggregations(
    sections_scan: pl.LazyFrame,
    group_cols: list[str],
) -> pl.LazyFrame:
    """Compute aggregate eligible voters, turnout, abstentions, and rates."""
    return (
        sections_scan.group_by(group_cols)
        .agg(
            [
                pl.len().alias("total_sections"),
                pl.col("eligible_voters").sum().alias("total_eligible_voters"),
                pl.col("actual_turnout").sum().alias("total_actual_turnout"),
                pl.col("abstentions").sum().alias("total_abstentions"),
            ]
        )
        .with_columns(
            [
                (
                    pl.when(pl.col("total_eligible_voters") > 0)
                    .then(pl.col("total_abstentions") * 100.0 / pl.col("total_eligible_voters"))
                    .otherwise(0.0)
                ).alias("abstention_rate_pct"),
                (
                    pl.when(pl.col("total_eligible_voters") > 0)
                    .then(pl.col("total_actual_turnout") * 100.0 / pl.col("total_eligible_voters"))
                    .otherwise(0.0)
                ).alias("turnout_rate_pct"),
            ]
        )
    )


def compute_votes_aggregations(
    votes_scan: pl.LazyFrame,
    group_cols: list[str],
) -> pl.LazyFrame:
    """Compute nominal, legenda, blank, and null vote sums and rates."""
    # vote_type_code: 1=Nominal, 2=Branco, 3=Nulo, 4=Legenda
    nominal_expr = (
        pl.when(pl.col("vote_type_code") == 1)
        .then(pl.col("vote_count"))
        .otherwise(0)
        .sum()
        .alias("total_nominal_votes")
    )
    legenda_expr = (
        pl.when(pl.col("vote_type_code") == 4)
        .then(pl.col("vote_count"))
        .otherwise(0)
        .sum()
        .alias("total_legenda_votes")
    )
    blank_expr = (
        pl.when(pl.col("vote_type_code") == 2)
        .then(pl.col("vote_count"))
        .otherwise(0)
        .sum()
        .alias("total_blank_votes")
    )
    null_expr = (
        pl.when(pl.col("vote_type_code") == 3)
        .then(pl.col("vote_count"))
        .otherwise(0)
        .sum()
        .alias("total_null_votes")
    )
    total_votes_expr = pl.col("vote_count").sum().alias("total_votes_cast")

    agg_df = votes_scan.group_by(group_cols).agg(
        [
            nominal_expr,
            legenda_expr,
            blank_expr,
            null_expr,
            total_votes_expr,
        ]
    )

    return agg_df.with_columns(
        [
            (pl.col("total_nominal_votes") + pl.col("total_legenda_votes")).alias(
                "total_valid_votes"
            ),
        ]
    ).with_columns(
        [
            (
                pl.when(pl.col("total_votes_cast") > 0)
                .then(pl.col("total_valid_votes") * 100.0 / pl.col("total_votes_cast"))
                .otherwise(0.0)
            ).alias("valid_vote_rate_pct"),
            (
                pl.when(pl.col("total_votes_cast") > 0)
                .then(pl.col("total_blank_votes") * 100.0 / pl.col("total_votes_cast"))
                .otherwise(0.0)
            ).alias("blank_vote_rate_pct"),
            (
                pl.when(pl.col("total_votes_cast") > 0)
                .then(pl.col("total_null_votes") * 100.0 / pl.col("total_votes_cast"))
                .otherwise(0.0)
            ).alias("null_vote_rate_pct"),
        ]
    )


def generate_gold_national_summary(
    repo: DataRepository, year: int = 2026, election_round: str = "2t"
) -> pl.DataFrame:
    """Generate national overview aggregation table."""
    sections_scan = repo.get_silver_scan(
        "polling_sections", year=year, election_round=election_round
    )
    votes_scan = repo.get_silver_scan("votes", year=year, election_round=election_round)

    base_groups = ["election_year", "election_round"]
    turnout_agg = compute_turnout_aggregations(sections_scan, base_groups)
    votes_agg = compute_votes_aggregations(votes_scan, base_groups + ["office_code"])

    joined = votes_agg.join(turnout_agg, on=base_groups, how="left")
    return joined.collect().sort(["election_round", "office_code"])


def generate_gold_state_summary(
    repo: DataRepository, year: int = 2026, election_round: str = "2t"
) -> pl.DataFrame:
    """Generate state-level summary table."""
    sections_scan = repo.get_silver_scan(
        "polling_sections", year=year, election_round=election_round
    )
    votes_scan = repo.get_silver_scan("votes", year=year, election_round=election_round)

    state_groups = ["election_year", "election_round", "state_abbreviation"]
    turnout_agg = compute_turnout_aggregations(sections_scan, state_groups)
    votes_agg = compute_votes_aggregations(votes_scan, state_groups + ["office_code"])

    joined = votes_agg.join(turnout_agg, on=state_groups, how="left")
    return joined.collect().sort(["election_round", "office_code", "state_abbreviation"])


def generate_gold_municipality_summary(
    repo: DataRepository, year: int = 2026, election_round: str = "2t"
) -> pl.DataFrame:
    """Generate municipality-level summary table."""
    sections_scan = repo.get_silver_scan(
        "polling_sections", year=year, election_round=election_round
    )
    votes_scan = repo.get_silver_scan("votes", year=year, election_round=election_round)

    muni_groups = [
        "election_year",
        "election_round",
        "state_abbreviation",
        "municipality_tse_code",
    ]
    turnout_agg = compute_turnout_aggregations(sections_scan, muni_groups)
    votes_agg = compute_votes_aggregations(votes_scan, muni_groups + ["office_code"])

    # Attach municipality name
    muni_names = sections_scan.select(
        ["state_abbreviation", "municipality_tse_code", "municipality_name"]
    ).unique()

    joined = (
        votes_agg.join(turnout_agg, on=muni_groups, how="left")
        .join(
            muni_names,
            on=["state_abbreviation", "municipality_tse_code"],
            how="left",
        )
        .collect()
        .sort(
            [
                "election_round",
                "office_code",
                "state_abbreviation",
                "municipality_name",
            ]
        )
    )
    return joined


def generate_gold_candidate_summary(
    repo: DataRepository, year: int = 2026, election_round: str = "2t"
) -> pl.DataFrame:
    """Generate candidate results and vote share rankings."""
    candidates_scan = repo.get_silver_scan("candidates", year=year, election_round=election_round)
    votes_scan = repo.get_silver_scan("votes", year=year, election_round=election_round)

    # Sum votes per candidate and office
    cand_votes = votes_scan.group_by(
        [
            "election_year",
            "election_round",
            "office_code",
            "ballot_number",
        ]
    ).agg(pl.col("vote_count").sum().alias("total_candidate_votes"))

    # Compute total valid votes per office
    valid_totals = (
        votes_scan.filter(pl.col("vote_type_code").is_in([1, 4]))
        .group_by(["election_year", "election_round", "office_code"])
        .agg(pl.col("vote_count").sum().alias("total_valid_votes"))
    )

    cand_meta = candidates_scan.select(
        [
            "election_year",
            "election_round",
            "office_code",
            "office_name",
            "ballot_number",
            "candidate_name",
            "party_number",
            "party_abbreviation",
            "vote_type_description",
        ]
    ).unique(
        subset=[
            "election_year",
            "election_round",
            "office_code",
            "ballot_number",
        ]
    )

    summary = (
        cand_votes.join(
            valid_totals,
            on=["election_year", "election_round", "office_code"],
            how="left",
        )
        .join(
            cand_meta,
            on=["election_year", "election_round", "office_code", "ballot_number"],
            how="left",
        )
        .with_columns(
            [
                (
                    pl.when(pl.col("total_valid_votes") > 0)
                    .then(pl.col("total_candidate_votes") * 100.0 / pl.col("total_valid_votes"))
                    .otherwise(0.0)
                ).alias("valid_vote_share_pct")
            ]
        )
        .collect()
        .sort(["office_code", "total_candidate_votes"], descending=[False, True])
    )

    # Add ranking within each office
    ranked = summary.with_columns(
        pl.col("total_candidate_votes")
        .rank(descending=True)
        .over(["election_round", "office_code"])
        .alias("rank")
    )
    return ranked


def write_gold_parquet(
    df: pl.DataFrame,
    gold_dir: Path,
    summary_name: str,
    year: int = 2026,
    election_round: str = "2t",
) -> Path:
    """Persist gold summary dataset to Parquet."""
    target_dir = gold_dir / str(year) / summary_name
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f"{summary_name}_{election_round}.parquet"
    df.write_parquet(target_file, compression="snappy")
    logger.info("Saved Gold summary to %s (%d rows)", target_file, len(df))
    return target_file
