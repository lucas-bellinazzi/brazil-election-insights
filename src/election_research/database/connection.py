"""DuckDB database connection manager and Parquet view registration."""

from pathlib import Path
from typing import Any

import duckdb

from election_research.core.config import get_settings
from election_research.core.exceptions import DatabaseError
from election_research.core.logging import get_logger

logger = get_logger(__name__)


def create_duckdb_views(conn: duckdb.DuckDBPyConnection, settings: Any = None) -> None:
    """Register standard views over partitioned Silver and Gold Parquet datasets."""
    settings = settings or get_settings()

    # 1. Silver Views
    silver_tables = ["elections", "polling_sections", "candidates", "votes"]
    for table in silver_tables:
        table_glob = (settings.silver_dir / "*" / table / "*/*.parquet").as_posix()
        try:
            conn.execute(
                f"""
                CREATE OR REPLACE VIEW silver_{table} AS
                SELECT * FROM read_parquet('{table_glob}')
                """
            )
            logger.debug("Registered view: silver_%s -> %s", table, table_glob)
        except Exception as e:
            logger.debug("Could not register silver_%s (files may not exist yet): %s", table, e)

    # 2. Gold Views
    gold_summaries = [
        "national_summary",
        "state_summary",
        "municipality_summary",
        "candidate_summary",
    ]
    for summary in gold_summaries:
        summary_glob = (settings.gold_dir / "*" / summary / "*.parquet").as_posix()
        try:
            conn.execute(
                f"""
                CREATE OR REPLACE VIEW gold_{summary} AS
                SELECT * FROM read_parquet('{summary_glob}')
                """
            )
            logger.debug("Registered view: gold_%s -> %s", summary, summary_glob)
        except Exception as e:
            logger.debug("Could not register gold_%s (files may not exist yet): %s", summary, e)


def get_connection(
    db_path: Path | str | None = None,
    read_only: bool = False,
    register_views: bool = True,
) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection and initialize analytical Parquet views."""
    settings = get_settings()

    if db_path is None:
        db_path = settings.duckdb_path

    if str(db_path) != ":memory:":
        db_path_obj = Path(db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        target = str(db_path_obj)
    else:
        target = ":memory:"

    try:
        # Enforce secure configuration: disable unauthorized extension downloading
        secure_config = {
            "allow_community_extensions": False,
            "autoinstall_known_extensions": False,
            "autoload_known_extensions": False,
        }
        conn = duckdb.connect(database=target, read_only=read_only, config=secure_config)
        # Configure resource limits and optimizations
        conn.execute("PRAGMA threads=4;")
        conn.execute("PRAGMA memory_limit='4GB';")

        if register_views:
            create_duckdb_views(conn, settings=settings)

        return conn
    except Exception as e:
        raise DatabaseError(f"Failed to connect to DuckDB at {target}: {e}") from e
