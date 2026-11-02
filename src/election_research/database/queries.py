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


def query_single_state(
    conn: duckdb.DuckDBPyConnection,
    state_code: str,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
) -> dict[str, Any]:
    """Retrieve full summary for an individual Brazilian state."""
    clean_uf = sanitize_uf(state_code)
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
        WHERE state_abbreviation = ? AND election_year = ? AND election_round = ? AND office_code = ?
        """
        rows = (
            conn.sql(sql, params=[clean_uf, int(year), int(election_round), int(office_code)])
            .limit(1)
            .fetchall()
        )
        if not rows:
            return {}
        cols = [
            "state_abbreviation",
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
        return dict(zip(cols, rows[0], strict=False))
    except Exception as e:
        raise DatabaseError(f"Failed to query state {clean_uf}: {e}") from e


def query_single_municipality(
    conn: duckdb.DuckDBPyConnection,
    municipality_code_or_name: str,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
) -> dict[str, Any]:
    """Retrieve full summary for a municipality by TSE code or name."""
    try:
        # Check if argument is numeric TSE code or name
        is_code = municipality_code_or_name.strip().isdigit()
        if is_code:
            where_clause = "municipality_tse_code = ?"
            param_val = int(municipality_code_or_name.strip())
        else:
            where_clause = "municipality_name ILIKE ?"
            param_val = f"%{municipality_code_or_name.strip()}%"

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
        WHERE {where_clause} AND election_year = ? AND election_round = ? AND office_code = ?
        """
        rows = (
            conn.sql(sql, params=[param_val, int(year), int(election_round), int(office_code)])
            .limit(1)
            .fetchall()
        )
        if not rows:
            return {}
        cols = [
            "state_abbreviation",
            "municipality_tse_code",
            "municipality_name",
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
        ]
        return dict(zip(cols, rows[0], strict=False))
    except Exception as e:
        raise DatabaseError(f"Failed to query municipality {municipality_code_or_name}: {e}") from e


def query_polling_section_detail(
    conn: duckdb.DuckDBPyConnection,
    state_code: str,
    section_number: int,
    municipality_code: str | None = None,
    year: int = 2026,
    election_round: int = 2,
) -> dict[str, Any]:
    """Retrieve details of an individual polling station from the Silver layer."""
    clean_uf = sanitize_uf(state_code)
    try:
        conditions = [
            "state_abbreviation = ?",
            "polling_section = ?",
            "election_year = ?",
            "election_round = ?",
        ]
        params: list[Any] = [clean_uf, int(section_number), int(year), int(election_round)]

        if municipality_code:
            if municipality_code.strip().isdigit():
                conditions.append("municipality_tse_code = ?")
                params.append(int(municipality_code.strip()))
            else:
                conditions.append("municipality_name ILIKE ?")
                params.append(f"%{municipality_code.strip()}%")

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
        """
        rows = conn.sql(sql, params=params).limit(1).fetchall()
        if not rows:
            return {}
        cols = [
            "state_abbreviation",
            "municipality_name",
            "electoral_zone",
            "polling_section",
            "voting_location_number",
            "eligible_voters",
            "actual_turnout",
            "abstentions",
            "abstention_rate_pct",
            "urn_type_description",
            "urn_serial_number",
            "poll_opened_at",
            "poll_closed_at",
        ]
        return dict(zip(cols, rows[0], strict=False))
    except Exception as e:
        raise DatabaseError(
            f"Failed to query polling section {section_number} ({clean_uf}): {e}"
        ) from e


def query_closing_time_overview(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    uf: str | None = None,
) -> dict[str, Any]:
    """Retrieve national or state-level summary indicators for polling section closing times."""
    try:
        where_clauses = ["election_year = ?", "election_round = ?"]
        params: list[Any] = [year, election_round]
        if uf:
            clean_uf = sanitize_uf(uf)
            where_clauses.append("state_abbreviation = ?")
            params.append(clean_uf)

        where_str = " AND ".join(where_clauses)

        sql = f"""
        WITH normalized AS (
            SELECT 
                state_abbreviation,
                eligible_voters,
                actual_turnout,
                abstentions,
                CASE 
                    WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
                    WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
                    ELSE CAST(poll_closed_at AS TIMESTAMP)
                END as poll_closed_brt
            FROM silver_polling_sections
            WHERE {where_str}
        )
        SELECT 
            COUNT(*) as total_sections,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN 1 END) as regular_count,
            ROUND(COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as regular_pct,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) as extended_count,
            ROUND(COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as extended_pct,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') BETWEEN '18:30' AND '19:05' THEN 1 END) as full_extended_count,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') > '19:05' THEN 1 END) as late_queues_count,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN actual_turnout ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as regular_turnout_pct,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN actual_turnout ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as extended_turnout_pct,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN abstentions ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as regular_abstention_pct,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN abstentions ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as extended_abstention_pct
        FROM normalized
        """
        rows = conn.sql(sql, params=params).fetchall()
        if not rows:
            return {}
        cols = [
            "total_sections",
            "regular_count",
            "regular_pct",
            "extended_count",
            "extended_pct",
            "full_extended_count",
            "late_queues_count",
            "regular_turnout_pct",
            "extended_turnout_pct",
            "regular_abstention_pct",
            "extended_abstention_pct",
        ]
        return dict(zip(cols, rows[0], strict=False))
    except Exception as e:
        raise DatabaseError(f"Failed to query closing time overview: {e}") from e


def query_closing_time_timeline(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    uf: str | None = None,
    bucket_minutes: int = 5,
) -> pl.DataFrame:
    """Retrieve temporal progression of polling section closures binned by intervals in BRT."""
    try:
        where_clauses = ["election_year = ?", "election_round = ?"]
        params: list[Any] = [year, election_round]
        if uf:
            clean_uf = sanitize_uf(uf)
            where_clauses.append("state_abbreviation = ?")
            params.append(clean_uf)

        where_str = " AND ".join(where_clauses)
        interval_str = f"{int(bucket_minutes)} MINUTES"

        sql = f"""
        WITH normalized AS (
            SELECT 
                eligible_voters,
                actual_turnout,
                abstentions,
                CASE 
                    WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
                    WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
                    ELSE CAST(poll_closed_at AS TIMESTAMP)
                END as poll_closed_brt
            FROM silver_polling_sections
            WHERE {where_str}
        ),
        binned AS (
            SELECT 
                strftime(time_bucket(INTERVAL '{interval_str}', poll_closed_brt), '%H:%M') as bin_time,
                COUNT(*) as num_sections,
                SUM(eligible_voters) as total_eligible,
                SUM(actual_turnout) as total_turnout,
                SUM(abstentions) as total_abstentions
            FROM normalized
            GROUP BY bin_time
            ORDER BY bin_time
        )
        SELECT 
            bin_time,
            num_sections,
            SUM(num_sections) OVER (ORDER BY bin_time) as cumulative_sections,
            ROUND(SUM(num_sections) OVER (ORDER BY bin_time) * 100.0 / NULLIF(SUM(num_sections) OVER (), 0), 2) as cumulative_pct,
            total_eligible,
            total_turnout,
            total_abstentions,
            ROUND(total_turnout * 100.0 / NULLIF(total_eligible, 0), 2) as turnout_pct,
            ROUND(total_abstentions * 100.0 / NULLIF(total_eligible, 0), 2) as abstention_pct
        FROM binned
        ORDER BY bin_time
        """
        arrow_table = conn.sql(sql, params=params).arrow()
        return pl.from_arrow(arrow_table)
    except Exception as e:
        raise DatabaseError(f"Failed to query closing time timeline: {e}") from e


def query_closing_time_by_state(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
) -> pl.DataFrame:
    """Retrieve state-by-state comparison of regular vs extended section closures."""
    try:
        sql = """
        WITH normalized AS (
            SELECT 
                state_abbreviation,
                eligible_voters,
                actual_turnout,
                abstentions,
                CASE 
                    WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
                    WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
                    ELSE CAST(poll_closed_at AS TIMESTAMP)
                END as poll_closed_brt
            FROM silver_polling_sections
            WHERE election_year = ? AND election_round = ?
        )
        SELECT 
            state_abbreviation,
            COUNT(*) as total_sections,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN 1 END) as regular_sections,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) as extended_sections,
            ROUND(COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as pct_extended,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN actual_turnout ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as regular_turnout_pct,
            ROUND(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN actual_turnout ELSE 0 END) * 100.0 / 
                  NULLIF(SUM(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN eligible_voters ELSE 0 END), 0), 2) as extended_turnout_pct
        FROM normalized
        GROUP BY state_abbreviation
        ORDER BY pct_extended DESC
        """
        arrow_table = conn.sql(sql, params=[year, election_round]).arrow()
        return pl.from_arrow(arrow_table)
    except Exception as e:
        raise DatabaseError(f"Failed to query closing time by state: {e}") from e


def query_closing_time_candidates(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    office_code: int = 1,
    uf: str | None = None,
) -> pl.DataFrame:
    """Retrieve candidate vote totals and percentages partitioned across closing time regimes."""
    try:
        where_clauses = [
            "s.election_year = ?",
            "s.election_round = ?",
            "v.office_code = ?",
            "v.ballot_number IN (13, 22)",
        ]
        params: list[Any] = [year, election_round, office_code]
        if uf:
            clean_uf = sanitize_uf(uf)
            where_clauses.append("s.state_abbreviation = ?")
            params.append(clean_uf)

        votes_where_str = " AND ".join([w.replace("s.", "v.") for w in where_clauses])

        sql = f"""
        WITH normalized AS (
            SELECT 
                state_abbreviation,
                municipality_tse_code,
                electoral_zone,
                polling_section,
                CASE 
                    WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
                    WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
                    ELSE CAST(poll_closed_at AS TIMESTAMP)
                END as poll_closed_brt
            FROM silver_polling_sections
            WHERE election_year = {int(year)} AND election_round = {int(election_round)}
        ),
        classified AS (
            SELECT 
                state_abbreviation,
                municipality_tse_code,
                electoral_zone,
                polling_section,
                CASE 
                    WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN '1. Regular (17:00 - 17:09)'
                    WHEN strftime(poll_closed_brt, '%H:%M') < '18:30' THEN '2. Prorrogada Inicial (17:10 - 18:29)'
                    WHEN strftime(poll_closed_brt, '%H:%M') <= '19:05' THEN '3. Prorrogada Integral (18:30 - 19:05)'
                    ELSE '4. Filas Tardias (> 19:05)'
                END as closing_regime
            FROM normalized
        ),
        regime_votes AS (
            SELECT 
                c.closing_regime,
                v.ballot_number,
                cand.candidate_name,
                SUM(v.vote_count) as vote_count
            FROM silver_votes v
            JOIN classified c 
                ON v.state_abbreviation = c.state_abbreviation 
                AND v.municipality_tse_code = c.municipality_tse_code
                AND v.electoral_zone = c.electoral_zone
                AND v.polling_section = c.polling_section
            JOIN silver_candidates cand 
                ON v.ballot_number = cand.ballot_number 
                AND v.election_round = cand.election_round
                AND cand.office_code = v.office_code
            WHERE {votes_where_str}
            GROUP BY c.closing_regime, v.ballot_number, cand.candidate_name
        )
        SELECT 
            closing_regime,
            ballot_number,
            candidate_name,
            vote_count,
            SUM(vote_count) OVER (PARTITION BY closing_regime) as total_valid_in_regime,
            ROUND(vote_count * 100.0 / NULLIF(SUM(vote_count) OVER (PARTITION BY closing_regime), 0), 2) as vote_pct
        FROM regime_votes
        ORDER BY closing_regime, ballot_number
        """
        arrow_table = conn.sql(sql, params=params).arrow()
        return pl.from_arrow(arrow_table)
    except Exception as e:
        raise DatabaseError(f"Failed to query candidate votes by closing regime: {e}") from e


def query_closing_time_municipalities(
    conn: duckdb.DuckDBPyConnection,
    year: int = 2026,
    election_round: int = 2,
    uf: str | None = None,
    min_sections: int = 20,
    top_n: int = 25,
) -> pl.DataFrame:
    """Retrieve municipalities with highest count or proportion of extended polling sections."""
    try:
        where_clauses = ["election_year = ?", "election_round = ?"]
        params: list[Any] = [year, election_round]
        if uf:
            clean_uf = sanitize_uf(uf)
            where_clauses.append("state_abbreviation = ?")
            params.append(clean_uf)

        where_str = " AND ".join(where_clauses)

        sql = f"""
        WITH normalized AS (
            SELECT 
                state_abbreviation,
                municipality_name,
                eligible_voters,
                actual_turnout,
                abstentions,
                CASE 
                    WHEN state_abbreviation = 'AC' OR (state_abbreviation = 'AM' AND poll_closed_at LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 2 HOUR
                    WHEN state_abbreviation IN ('MT', 'MS', 'RO', 'RR') OR (state_abbreviation = 'AM' AND poll_closed_at NOT LIKE '% 15:%')
                        THEN CAST(poll_closed_at AS TIMESTAMP) + INTERVAL 1 HOUR
                    ELSE CAST(poll_closed_at AS TIMESTAMP)
                END as poll_closed_brt
            FROM silver_polling_sections
            WHERE {where_str}
        )
        SELECT 
            state_abbreviation,
            municipality_name,
            COUNT(*) as total_sections,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') < '17:10' THEN 1 END) as regular_sections,
            COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) as extended_sections,
            ROUND(COUNT(CASE WHEN strftime(poll_closed_brt, '%H:%M') >= '17:10' THEN 1 END) * 100.0 / NULLIF(COUNT(*), 0), 2) as pct_extended,
            SUM(actual_turnout) as total_turnout,
            SUM(abstentions) as total_abstentions,
            ROUND(SUM(abstentions) * 100.0 / NULLIF(SUM(eligible_voters), 0), 2) as abstention_rate_pct
        FROM normalized
        GROUP BY state_abbreviation, municipality_name
        HAVING COUNT(*) >= {int(min_sections)}
        ORDER BY extended_sections DESC, pct_extended DESC
        LIMIT {int(top_n)}
        """
        arrow_table = conn.sql(sql, params=params).arrow()
        return pl.from_arrow(arrow_table)
    except Exception as e:
        raise DatabaseError(f"Failed to query top municipalities by extended closing: {e}") from e
