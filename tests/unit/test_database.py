"""Unit tests for DuckDB database connection and queries."""

from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_candidate_rankings,
    query_electoral_overview,
    query_municipality_results,
    query_polling_sections,
    query_state_results,
)


def test_duckdb_connection_and_queries():
    conn = get_connection(db_path=":memory:", register_views=True)
    assert conn is not None

    # Test national summary query
    overview = query_electoral_overview(conn, year=2026, election_round=2, office_code=1)
    assert isinstance(overview, dict)
    assert "total_sections" in overview
    assert overview["total_sections"] > 0
    assert overview["total_eligible_voters"] > 0

    # Test state results query
    states_df = query_state_results(conn, year=2026, election_round=2, office_code=1)
    assert len(states_df) > 0
    assert "state_abbreviation" in states_df.columns
    assert "SP" in states_df["state_abbreviation"].to_list()

    # Test candidate rankings query
    cands_df = query_candidate_rankings(conn, year=2026, election_round=2, office_code=1)
    assert len(cands_df) > 0
    assert "rank" in cands_df.columns
    assert "valid_vote_share_pct" in cands_df.columns

    # Test municipality results query
    munis_df = query_municipality_results(
        conn, year=2026, election_round=2, office_code=1, uf="AC", limit=10
    )
    assert len(munis_df) > 0
    assert (munis_df["state_abbreviation"] == "AC").all()

    # Test polling sections query
    sections_df = query_polling_sections(conn, year=2026, election_round=2, uf="AC", limit=10)
    assert len(sections_df) > 0
    assert "polling_section" in sections_df.columns
