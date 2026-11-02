"""Unit tests for closing time analytics, queries, and visualizations."""

import numpy as np
import polars as pl
import pytest
from app.components.charts import (
    create_candidate_by_closing_regime_chart,
    create_closing_regime_donut,
    create_closing_timeline_chart,
    create_state_extension_bar_chart,
)

from election_research.analytics.closing_times import (
    classify_closing_regime,
    compare_regimes_turnout,
    compute_geographic_extension_disparity,
)
from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_closing_time_by_state,
    query_closing_time_candidates,
    query_closing_time_municipalities,
    query_closing_time_overview,
    query_closing_time_timeline,
)


class TestClosingTimeClassification:
    """Tests for regime categorization logic."""

    def test_classify_regular_regime(self):
        assert classify_closing_regime("2026-10-25 17:00:15") == "regular"
        assert classify_closing_regime("2026-10-25 17:09:59") == "regular"

    def test_classify_early_extension(self):
        assert classify_closing_regime("2026-10-25 17:10:00") == "early_extension"
        assert classify_closing_regime("2026-10-25 18:29:59") == "early_extension"

    def test_classify_full_extension(self):
        assert classify_closing_regime("2026-10-25 18:30:00") == "full_extension"
        assert classify_closing_regime("2026-10-25 19:00:12") == "full_extension"
        assert classify_closing_regime("2026-10-25 19:05:00") == "full_extension"

    def test_classify_late_queues(self):
        assert classify_closing_regime("2026-10-25 19:05:01") == "late_queues"
        assert classify_closing_regime("2026-10-25 20:15:00") == "late_queues"

    def test_classify_empty_or_none(self):
        assert classify_closing_regime("") == "regular"


class TestClosingTimeStatistics:
    """Tests for statistical comparison between regular and extended regimes."""

    def test_compare_regimes_turnout(self):
        regular = np.array([80.0, 81.0, 79.5, 80.5])
        extended = np.array([78.0, 77.5, 78.5, 77.0])
        res = compare_regimes_turnout(regular, extended)
        assert res["mean_regular"] > res["mean_extended"]
        assert res["diff_pct_points"] < 0
        assert res["statistically_significant"] is True

    def test_compute_geographic_disparity(self):
        df = pl.DataFrame(
            {
                "state_abbreviation": ["RJ", "BA", "SC"],
                "total_sections": [1000, 1000, 1000],
                "extended_sections": [100, 50, 2],
                "pct_extended": [10.0, 5.0, 0.2],
            }
        )
        res = compute_geographic_extension_disparity(df)
        assert res["highest_state"] == "RJ"
        assert res["highest_pct"] == 10.0
        assert res["lowest_state"] == "SC"
        assert res["lowest_pct"] == 0.2
        assert res["disparity_ratio"] == 50.0
        assert res["total_extended_sections"] == 152


class TestClosingTimeQueries:
    """Tests for DuckDB parameterized closing time queries."""

    @pytest.fixture
    def conn(self):
        return get_connection(read_only=True, register_views=True)

    def test_query_closing_time_overview_national(self, conn):
        ov = query_closing_time_overview(conn, year=2026, election_round=2)
        assert ov["total_sections"] > 400000
        assert ov["regular_count"] > 0
        assert ov["extended_count"] > 0
        assert ov["regular_pct"] > 90.0
        assert ov["extended_pct"] < 10.0

    def test_query_closing_time_overview_filtered_uf(self, conn):
        ov_rj = query_closing_time_overview(conn, year=2026, election_round=2, uf="RJ")
        assert ov_rj["total_sections"] > 30000
        assert ov_rj["extended_pct"] > 5.0

    def test_query_closing_time_timeline(self, conn):
        tl = query_closing_time_timeline(conn, year=2026, election_round=2, bucket_minutes=5)
        assert not tl.is_empty()
        assert "bin_time" in tl.columns
        assert "num_sections" in tl.columns
        assert "cumulative_pct" in tl.columns

    def test_query_closing_time_by_state(self, conn):
        st_df = query_closing_time_by_state(conn, year=2026, election_round=2)
        assert len(st_df) >= 27
        assert "pct_extended" in st_df.columns
        assert st_df["pct_extended"].max() > 0

    def test_query_closing_time_candidates(self, conn):
        cand_df = query_closing_time_candidates(conn, year=2026, election_round=2, office_code=1)
        assert not cand_df.is_empty()
        assert "closing_regime" in cand_df.columns
        assert "vote_pct" in cand_df.columns

    def test_query_closing_time_municipalities(self, conn):
        muni_df = query_closing_time_municipalities(conn, year=2026, election_round=2, top_n=10)
        assert len(muni_df) <= 10
        assert "extended_sections" in muni_df.columns


class TestClosingTimeVisualizations:
    """Tests for Plotly chart generators."""

    def test_charts_generate_cleanly(self):
        timeline_df = pl.DataFrame(
            {
                "bin_time": ["17:00", "17:05", "19:00"],
                "num_sections": [1000, 200, 50],
                "cumulative_pct": [80.0, 96.0, 100.0],
            }
        )
        fig_tl = create_closing_timeline_chart(timeline_df)
        assert fig_tl is not None

        overview = {
            "regular_count": 900,
            "extended_count": 100,
            "full_extended_count": 80,
            "late_queues_count": 5,
        }
        fig_donut = create_closing_regime_donut(overview)
        assert fig_donut is not None

        state_df = pl.DataFrame(
            {
                "state_abbreviation": ["RJ", "SP"],
                "total_sections": [1000, 2000],
                "extended_sections": [100, 60],
                "pct_extended": [10.0, 3.0],
            }
        )
        fig_states = create_state_extension_bar_chart(state_df)
        assert fig_states is not None

        cand_df = pl.DataFrame(
            {
                "closing_regime": ["1. Regular (17:00 - 17:09)", "2. Prorrogada (17:10 - 19:05)"],
                "candidate_name": ["LULA", "LULA"],
                "vote_pct": [51.5, 56.2],
            }
        )
        fig_cand = create_candidate_by_closing_regime_chart(cand_df)
        assert fig_cand is not None
