"""Parameterized analytical SQL queries executed via DuckDB over Parquet views."""

from typing import Any

import duckdb
import polars as pl

from election_research.core.exceptions import DatabaseError
from election_research.core.logging import get_logger
from election_research.core.security import sanitize_uf

logger = get_logger(__name__)


def query_electoral_overview(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
) -> dict[str, Any]:
    """Retrieve key high-level national indicators for an election."""
    try:
        sql = """
        SELECT
            total_sections,
            total_eligible_voters,
            total_actual_turnout,
            total_abstentions,
            turnout_rate_pct,
            abstention_rate_pct,
            total_valid_votes,
            total_blank_votes,
            total_null_votes,
            valid_vote_rate_pct,
            blank_vote_rate_pct,
            null_vote_rate_pct
        FROM gold_national_summary
        WHERE election_year = ? AND election_round = ? AND office_code = ?
        """
        rows = conn.sql(sql, params=[year, election_round, office_code]).limit(1).fetchall()
        if not rows:
            return {}
        row = rows[0]

        cols = [
            "total_sections",
            "total_eligible_voters",
            "total_actual_turnout",
            "total_abstentions",
            "turnout_rate_pct",
            "abstention_rate_pct",
            "total_valid_votes",
            "total_blank_votes",
            "total_null_votes",
            "valid_vote_rate_pct",
            "blank_vote_rate_pct",
            "null_vote_rate_pct",
        ]
        return dict(zip(cols, row, strict=False))
    except Exception as e:
        raise DatabaseError(f"Failed to query electoral overview: {e}") from e


def query_state_results(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
) -> pl.DataFrame:
    """Retrieve state-level indicators."""
    try:
        sql = """
        SELECT
            state_abbreviation,
            total_sections,
            total_eligible_voters,
            total_actual_turnout,
            total_abstentions,
            turnout_rate_pct,
            abstention_rate_pct,
            total_valid_votes,
            total_blank_votes,
            total_null_votes,
            valid_vote_rate_pct,
            blank_vote_rate_pct,
            null_vote_rate_pct
        FROM gold_state_summary
        WHERE election_year = ? AND election_round = ? AND office_code = ?
        ORDER BY state_abbreviation
        """
        return conn.sql(sql, params=[year, election_round, office_code]).pl()
    except Exception as e:
        raise DatabaseError(f"Failed to query state results: {e}") from e


def query_municipality_results(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
    uf: str | None = None,
    name_filter: str | None = None,
    limit: int = 100,
) -> pl.DataFrame:
    """Retrieve municipality-level results with parameterized filtering."""
    try:
        clean_uf = sanitize_uf(uf)
        safe_limit = max(1, min(int(limit), 10_000))
        conditions = ["election_year = ?", "election_round = ?", "office_code = ?"]
        params: list[Any] = [int(year), int(election_round), int(office_code)]

        if clean_uf:
            conditions.append("state_abbreviation = ?")
            params.append(clean_uf)

        if name_filter:
            conditions.append("municipality_name ILIKE ?")
            params.append(f"%{name_filter}%")

        params.append(safe_limit)

        sql = f"""
        SELECT
            state_abbreviation,
            municipality_tse_code,
            municipality_name,
            total_sections,
            total_eligible_voters,
            total_actual_turnout,
            total_abstentions,
            turnout_rate_pct,
            abstention_rate_pct,
            total_valid_votes,
            total_blank_votes,
            total_null_votes,
            valid_vote_rate_pct
        FROM gold_municipality_summary
        WHERE {" AND ".join(conditions)}
        ORDER BY state_abbreviation, municipality_name
        LIMIT ?
        """
        return conn.sql(sql, params=params).pl()
    except Exception as e:
        raise DatabaseError(f"Failed to query municipality results: {e}") from e


def query_candidate_rankings(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
) -> pl.DataFrame:
    """Retrieve candidate rankings, vote counts, and vote percentages."""
    try:
        sql = """
        SELECT
            rank,
            ballot_number,
            candidate_name,
            party_number,
            party_abbreviation,
            vote_type_description,
            total_candidate_votes,
            valid_vote_share_pct
        FROM gold_candidate_summary
        WHERE election_year = ? AND election_round = ? AND office_code = ?
        ORDER BY rank
        """
        return conn.sql(sql, params=[year, election_round, office_code]).pl()
    except Exception as e:
        raise DatabaseError(f"Failed to query candidate rankings: {e}") from e


def query_polling_sections(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    uf: str = "AC",
    zone: int | None = None,
    limit: int = 100,
) -> pl.DataFrame:
    """Query polling sections from the Silver layer."""
    try:
        clean_uf = sanitize_uf(uf) or "AC"
        safe_limit = max(1, min(int(limit), 10_000))
        conditions = [
            "election_year = ?",
            "election_round = ?",
            "state_abbreviation = ?",
        ]
        params: list[Any] = [int(year), int(election_round), clean_uf]

        if zone is not None:
            conditions.append("electoral_zone = ?")
            params.append(int(zone))

        params.append(safe_limit)

        sql = f"""
        SELECT
            state_abbreviation,
            municipality_name,
            electoral_zone,
            polling_section,
            voting_location_number,
            eligible_voters,
            actual_turnout,
            abstentions,
            ROUND(abstentions * 100.0 / NULLIF(eligible_voters, 0), 2) AS abstention_rate_pct,
            urn_type_description,
            urn_serial_number,
            poll_opened_at,
            poll_closed_at
        FROM silver_polling_sections
        WHERE {" AND ".join(conditions)}
        ORDER BY electoral_zone, polling_section
        LIMIT ?
        """
        return conn.sql(sql, params=params).pl()
    except Exception as e:
        raise DatabaseError(f"Failed to query polling sections: {e}") from e


def query_top_abstention_municipalities(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
    min_voters: int = 5000,
    top_n: int = 10,
) -> pl.DataFrame:
    """Identify municipalities with highest abstention rates."""
    try:
        safe_top_n = max(1, min(int(top_n), 1000))
        safe_min_voters = max(0, int(min_voters))
        sql = """
        SELECT
            state_abbreviation,
            municipality_name,
            total_eligible_voters,
            total_actual_turnout,
            total_abstentions,
            abstention_rate_pct,
            turnout_rate_pct
        FROM gold_municipality_summary
        WHERE election_year = ? AND election_round = ? AND office_code = ?
          AND total_eligible_voters >= ?
        ORDER BY abstention_rate_pct DESC
        LIMIT ?
        """
        return conn.sql(
            sql,
            params=[int(year), int(election_round), int(office_code), safe_min_voters, safe_top_n],
        ).pl()
    except Exception as e:
        raise DatabaseError(f"Failed to query top abstention municipalities: {e}") from e
