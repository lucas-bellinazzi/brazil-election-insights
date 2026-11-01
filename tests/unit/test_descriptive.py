"""Unit tests for descriptive statistics and Gold layer aggregations."""

from pathlib import Path

import polars as pl

from election_research.analytics.descriptive import (
    compute_turnout_aggregations,
    compute_votes_aggregations,
    write_gold_parquet,
)


def test_compute_turnout_aggregations():
    sections = pl.DataFrame(
        {
            "election_year": [2026, 2026],
            "election_round": [2, 2],
            "eligible_voters": [400, 600],
            "actual_turnout": [320, 480],
            "abstentions": [80, 120],
        }
    ).lazy()

    agg = compute_turnout_aggregations(sections, ["election_year", "election_round"]).collect()
    assert len(agg) == 1
    assert agg["total_sections"][0] == 2
    assert agg["total_eligible_voters"][0] == 1000
    assert agg["total_actual_turnout"][0] == 800
    assert agg["total_abstentions"][0] == 200
    assert agg["turnout_rate_pct"][0] == 80.0
    assert agg["abstention_rate_pct"][0] == 20.0


def test_compute_votes_aggregations():
    votes = pl.DataFrame(
        {
            "election_year": [2026, 2026, 2026],
            "election_round": [2, 2, 2],
            "office_code": [1, 1, 1],
            "vote_type_code": [1, 2, 3],  # Nominal, Branco, Nulo
            "vote_count": [80, 10, 10],
        }
    ).lazy()

    group_cols = ["election_year", "election_round", "office_code"]
    agg = compute_votes_aggregations(votes, group_cols).collect()
    assert len(agg) == 1
    assert agg["total_nominal_votes"][0] == 80
    assert agg["total_valid_votes"][0] == 80
    assert agg["total_blank_votes"][0] == 10
    assert agg["total_null_votes"][0] == 10
    assert agg["total_votes_cast"][0] == 100
    assert agg["valid_vote_rate_pct"][0] == 80.0
    assert agg["blank_vote_rate_pct"][0] == 10.0
    assert agg["null_vote_rate_pct"][0] == 10.0


def test_write_gold_parquet(tmp_path: Path):
    gold_dir = tmp_path / "gold"
    df = pl.DataFrame({"metric": ["a", "b"], "val": [1, 2]})
    written = write_gold_parquet(df, gold_dir, "test_summary", year=2026, election_round="2t")
    assert written.is_file()
    assert written.name == "test_summary_2t.parquet"
