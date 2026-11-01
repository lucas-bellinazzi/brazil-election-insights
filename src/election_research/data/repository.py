"""Repository layer providing unified access to Silver Parquet datasets."""

import polars as pl

from election_research.core.config import get_settings
from election_research.core.exceptions import DataSourceError
from election_research.core.logging import get_logger
from election_research.core.security import (
    sanitize_election_round,
    sanitize_table_name,
    sanitize_uf,
    sanitize_year,
)

logger = get_logger(__name__)

ALLOWED_SILVER_TABLES = frozenset({"elections", "polling_sections", "candidates", "votes"})


class DataRepository:
    """Repository accessing Silver and Gold columnar data via Polars LazyFrames."""

    def __init__(self, settings=None) -> None:
        self.settings = settings or get_settings()

    def get_silver_scan(
        self,
        table_name: str,
        year: int = 2026,
        election_round: str | None = None,
        uf: str | None = None,
    ) -> pl.LazyFrame:
        """Return a Polars LazyFrame scanning the target partitioned Silver Parquet files."""
        safe_table = sanitize_table_name(table_name, ALLOWED_SILVER_TABLES)
        safe_year = sanitize_year(year)
        safe_round = sanitize_election_round(election_round)
        safe_uf = sanitize_uf(uf)

        base_dir = self.settings.silver_dir / str(safe_year) / safe_table
        if not base_dir.is_dir():
            raise DataSourceError(
                f"Silver directory not found for table '{safe_table}': {base_dir}"
            )

        round_part = f"round={safe_round}" if safe_round != "all" else "*"
        uf_part = f"{safe_table}_{safe_uf}.parquet" if safe_uf else "*.parquet"

        glob_pattern = str(base_dir / round_part / uf_part)
        matching = list(base_dir.glob(f"{round_part}/{uf_part}"))
        if not matching:
            raise DataSourceError(
                f"No parquet files match pattern '{glob_pattern}' for table '{table_name}'"
            )

        return pl.scan_parquet(glob_pattern)

    def load_elections(self, year: int = 2026, election_round: str | None = None) -> pl.DataFrame:
        """Retrieve distinct elections metadata."""
        return (
            self.get_silver_scan("elections", year=year, election_round=election_round)
            .collect()
            .unique()
        )

    def load_candidates(
        self,
        year: int = 2026,
        election_round: str | None = None,
        office_code: int | None = None,
    ) -> pl.DataFrame:
        """Retrieve candidates dataset."""
        scan = self.get_silver_scan("candidates", year=year, election_round=election_round)
        if office_code is not None:
            scan = scan.filter(pl.col("office_code") == office_code)
        return scan.collect().unique(
            subset=["election_year", "election_round", "office_code", "ballot_number"]
        )

    def load_polling_sections(
        self,
        year: int = 2026,
        election_round: str | None = None,
        uf: str | None = None,
    ) -> pl.DataFrame:
        """Retrieve polling sections dataset."""
        return self.get_silver_scan(
            "polling_sections", year=year, election_round=election_round, uf=uf
        ).collect()

    def load_votes(
        self,
        year: int = 2026,
        election_round: str | None = None,
        uf: str | None = None,
        office_code: int | None = None,
    ) -> pl.DataFrame:
        """Retrieve votes fact records."""
        scan = self.get_silver_scan("votes", year=year, election_round=election_round, uf=uf)
        if office_code is not None:
            scan = scan.filter(pl.col("office_code") == office_code)
        return scan.collect()
