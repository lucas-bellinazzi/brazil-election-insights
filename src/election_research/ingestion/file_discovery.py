"""Discovery and metadata extraction for raw Bronze TSE datasets."""

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from election_research.core.logging import get_logger
from election_research.core.security import (
    sanitize_election_round,
    sanitize_uf,
    sanitize_year,
    validate_safe_path,
)

logger = get_logger(__name__)

# TSE pattern: bweb_{round}_{uf}_{timestamp}.csv (e.g., bweb_1t_AC_051020261403.csv)
FILENAME_PATTERN = re.compile(
    r"^bweb_(?P<round>[12]t)_(?P<uf>[A-Z]{2})_(?P<timestamp>\d+)\.csv$", re.IGNORECASE
)


@dataclass(frozen=True)
class BronzeFileInfo:
    """Metadata for an individual raw TSE CSV file."""

    file_path: Path
    file_name: str
    year: int
    election_round: str
    uf: str
    file_timestamp: str
    size_bytes: int

    def to_dict(self) -> dict:
        d = asdict(self)
        d["file_path"] = str(self.file_path)
        return d


def parse_bronze_filename(file_path: Path, year: int) -> BronzeFileInfo | None:
    """Extract metadata from standard TSE BWeb filename."""
    name = file_path.name
    match = FILENAME_PATTERN.match(name)
    if not match:
        return None

    size = file_path.stat().st_size if file_path.is_file() else 0
    return BronzeFileInfo(
        file_path=file_path,
        file_name=name,
        year=year,
        election_round=match.group("round").lower(),
        uf=match.group("uf").upper(),
        file_timestamp=match.group("timestamp"),
        size_bytes=size,
    )


def discover_bronze_files(
    bronze_dir: Path,
    year: int = 2026,
    election_round: str | None = None,
    uf: str | None = None,
) -> list[BronzeFileInfo]:
    """Discover all raw Bronze CSV files matching optional year, round, and UF filters."""
    safe_year = sanitize_year(year)
    safe_round = sanitize_election_round(election_round)
    safe_uf = sanitize_uf(uf)

    year_dir = bronze_dir / "tse" / str(safe_year)
    if not year_dir.is_dir():
        # Fallback to direct bronze_dir / str(safe_year) if structure differs
        fallback = bronze_dir / str(safe_year)
        year_dir = fallback if fallback.is_dir() else year_dir

    if not year_dir.is_dir():
        logger.warning("Bronze year directory not found: %s", year_dir)
        return []

    round_subdirs = [safe_round] if safe_round != "all" else ["1t", "2t"]
    discovered: list[BronzeFileInfo] = []

    for rnd in round_subdirs:
        round_dir = year_dir / rnd
        if not round_dir.is_dir():
            continue

        for csv_file in round_dir.glob("*.csv"):
            validate_safe_path(csv_file, bronze_dir)
            info = parse_bronze_filename(csv_file, year=safe_year)
            if info:
                if safe_uf and info.uf != safe_uf:
                    continue
                discovered.append(info)

    return sorted(discovered, key=lambda x: (x.election_round, x.uf))


def get_official_checksum_file(csv_path: Path) -> Path | None:
    """Locate matching .sha512 file in the same directory if present."""
    candidate = csv_path.with_suffix(".csv.sha512")
    if candidate.is_file():
        return candidate
    candidate2 = csv_path.with_suffix(".sha512")
    return candidate2 if candidate2.is_file() else None
