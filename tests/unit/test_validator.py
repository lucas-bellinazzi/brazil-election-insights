"""Unit tests for data validator."""

import polars as pl

from election_research.data.validator import validate_silver_data


def test_validator_identifies_clean_data():
    df = pl.DataFrame(
        {
            "state_abbreviation": ["AC", "AC"],
            "municipality_tse_code": [1392, 1392],
            "electoral_zone": [1, 1],
            "polling_section": [10, 20],
            "office_code": [1, 1],
            "ballot_number": [13, 22],
            "vote_count": [150, 120],
            "eligible_voters": [400, 400],
            "actual_turnout": [320, 320],
            "abstentions": [80, 80],
        }
    )
    valid, rejected, report = validate_silver_data(df)
    assert len(valid) == 2
    assert len(rejected) == 0
    assert report.valid_records == 2
    assert report.rejected_records == 0


def test_validator_detects_turnout_mismatch():
    df = pl.DataFrame(
        {
            "state_abbreviation": ["AC"],
            "municipality_tse_code": [1392],
            "electoral_zone": [1],
            "polling_section": [10],
            "office_code": [1],
            "ballot_number": [13],
            "vote_count": [150],
            "eligible_voters": [400],
            "actual_turnout": [300],
            "abstentions": [50],  # 300 + 50 != 400
        }
    )
    valid, rejected, report = validate_silver_data(df)
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "TURNOUT_BALANCE_MISMATCH" in report.rejection_reasons


def test_validator_detects_negative_votes():
    df = pl.DataFrame(
        {
            "state_abbreviation": ["AC"],
            "municipality_tse_code": [1392],
            "electoral_zone": [1],
            "polling_section": [10],
            "office_code": [1],
            "ballot_number": [13],
            "vote_count": [-5],
            "eligible_voters": [400],
            "actual_turnout": [320],
            "abstentions": [80],
        }
    )
    valid, rejected, report = validate_silver_data(df)
    assert len(valid) == 0
    assert len(rejected) == 1
    assert "NEGATIVE_COUNTS" in report.rejection_reasons
