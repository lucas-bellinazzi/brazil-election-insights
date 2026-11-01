"""Unit tests for Silver table transformer and writer."""

from pathlib import Path

import polars as pl

from election_research.data.transformer import transform_to_silver_tables, write_silver_parquet


def test_transform_to_silver_tables():
    df = pl.DataFrame(
        {
            "election_year": [2026, 2026],
            "election_round": [2, 2],
            "election_code": [6258, 6258],
            "election_description": ["Eleição Geral", "Eleição Geral"],
            "election_type_code": [0, 0],
            "election_type_name": ["Ordinária", "Ordinária"],
            "election_date": ["2026-10-25", "2026-10-25"],
            "state_abbreviation": ["AC", "AC"],
            "municipality_tse_code": [1392, 1392],
            "municipality_name": ["RIO BRANCO", "RIO BRANCO"],
            "electoral_zone": [1, 1],
            "polling_section": [10, 10],
            "voting_location_number": [1001, 1001],
            "eligible_voters": [400, 400],
            "actual_turnout": [320, 320],
            "abstentions": [80, 80],
            "urn_type_code": [1, 1],
            "urn_type_description": ["Apurada", "Apurada"],
            "urn_serial_number": ["123", "123"],
            "urn_loaded_at": ["2026-09-15", "2026-09-15"],
            "poll_opened_at": ["2026-10-25 08:00", "2026-10-25 08:00"],
            "poll_closed_at": ["2026-10-25 17:00", "2026-10-25 17:00"],
            "bu_printed_at": ["2026-10-25 17:05", "2026-10-25 17:05"],
            "bu_received_at": ["2026-10-25 20:00", "2026-10-25 20:00"],
            "voters_without_biometrics": [0, 0],
            "office_code": [1, 1],
            "office_name": ["Presidente", "Presidente"],
            "ballot_number": [13, 22],
            "candidate_name": ["CANDIDATO A", "CANDIDATO B"],
            "party_number": [13, 22],
            "party_abbreviation": ["PT", "PL"],
            "party_name": ["PT", "PL"],
            "vote_type_code": [1, 1],
            "vote_type_description": ["Nominal", "Nominal"],
            "vote_count": [180, 120],
            "source_file": ["test.csv", "test.csv"],
        }
    )

    tables = transform_to_silver_tables(df)
    assert "elections" in tables
    assert "polling_sections" in tables
    assert "candidates" in tables
    assert "votes" in tables

    # elections should be deduplicated to 1
    assert len(tables["elections"]) == 1
    # polling_sections should be deduplicated to 1 section
    assert len(tables["polling_sections"]) == 1
    # candidates should have 2 candidates
    assert len(tables["candidates"]) == 2
    # votes should have 2 rows
    assert len(tables["votes"]) == 2


def test_write_silver_parquet(tmp_path: Path):
    silver_dir = tmp_path / "silver"
    mock_df = pl.DataFrame({"id": [1, 2], "val": ["a", "b"]})
    tables = {"test_table": mock_df}

    written = write_silver_parquet(tables, silver_dir, year=2026, election_round="2t", uf="AC")
    assert "test_table" in written
    assert written["test_table"].is_file()
    assert written["test_table"].name == "test_table_AC.parquet"
