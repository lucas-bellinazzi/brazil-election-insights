"""Session state management and cached database connection for Streamlit."""

import streamlit as st

from election_research.core.config import get_settings
from election_research.database.connection import get_connection


@st.cache_resource
def get_cached_database():
    """Return a cached DuckDB connection with pre-registered Parquet views."""
    settings = get_settings()
    return get_connection(db_path=settings.duckdb_path, read_only=True, register_views=True)


def init_session_state() -> None:
    """Initialize default session state keys if not already present."""
    if "selected_year" not in st.session_state:
        st.session_state.selected_year = 2026
    if "selected_round" not in st.session_state:
        st.session_state.selected_round = 2
    if "selected_office" not in st.session_state:
        st.session_state.selected_office = 1  # Presidente
    if "selected_uf" not in st.session_state:
        st.session_state.selected_uf = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
