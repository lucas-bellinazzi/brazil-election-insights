"""CSV inspection utilities for TSE raw datasets."""

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from election_research.core.exceptions import DataSourceError
from election_research.core.logging import get_logger

logger = get_logger(__name__)

CANDIDATE_ENCODINGS = ["iso-8859-1", "cp1252", "utf-8", "latin1"]
CANDIDATE_DELIMITERS = [";", ",", "\t"]


@dataclass(frozen=True)
class CSVInspectionResult:
    """Detailed summary of a CSV file structure and sample data."""

    file_path: str
    file_size_bytes: int
    encoding: str
    delimiter: str
    column_count: int
    columns: list[str]
    sample_row: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def detect_encoding(file_path: Path, sample_size: int = 65536) -> str:
    """Detect encoding by attempting decode on a raw byte sample."""
    if not file_path.is_file():
        raise DataSourceError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        sample = f.read(sample_size)

    for enc in CANDIDATE_ENCODINGS:
        try:
            sample.decode(enc)
            return enc
        except (UnicodeDecodeError, LookupError):
            continue

    return "iso-8859-1"


def detect_delimiter(file_path: Path, encoding: str, sample_lines: int = 5) -> str:
    """Detect delimiter by testing common delimiters on the first lines."""
    with open(file_path, encoding=encoding, errors="replace") as f:
        lines = [f.readline() for _ in range(sample_lines)]

    for delim in CANDIDATE_DELIMITERS:
        counts = [line.count(delim) for line in lines if line.strip()]
        if counts and len(set(counts)) == 1 and counts[0] > 0:
            return delim

    # Default for TSE files
    return ";"


def inspect_csv_file(file_path: Path) -> CSVInspectionResult:
    """Perform comprehensive inspection of a single CSV file."""
    if not file_path.is_file():
        raise DataSourceError(f"Target is not a valid file: {file_path}")

    encoding = detect_encoding(file_path)
    delimiter = detect_delimiter(file_path, encoding=encoding)
    file_size = file_path.stat().st_size

    with open(file_path, encoding=encoding, errors="replace") as f:
        reader = csv.reader(f, delimiter=delimiter)
        try:
            raw_headers = next(reader)
        except StopIteration as e:
            raise DataSourceError(f"Empty CSV file: {file_path}") from e

        columns = [h.strip().strip('"') for h in raw_headers]

        sample_row: dict[str, str] = {}
        try:
            raw_row = next(reader)
            sample_row = {
                col: (val.strip().strip('"') if isinstance(val, str) else str(val))
                for col, val in zip(columns, raw_row, strict=False)
            }
        except StopIteration:
            pass

    return CSVInspectionResult(
        file_path=str(file_path),
        file_size_bytes=file_size,
        encoding=encoding,
        delimiter=delimiter,
        column_count=len(columns),
        columns=columns,
        sample_row=sample_row,
    )


def inspect_directory_files(directory: Path, pattern: str = "*.csv") -> list[CSVInspectionResult]:
    """Inspect all CSV files matching the pattern within a directory."""
    if not directory.is_dir():
        logger.warning("Directory does not exist: %s", directory)
        return []

    results = []
    for f in sorted(directory.glob(pattern)):
        if f.is_file():
            results.append(inspect_csv_file(f))
    return results
