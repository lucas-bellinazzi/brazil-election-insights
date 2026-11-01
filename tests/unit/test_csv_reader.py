"""Unit tests for CSV reader and inspection utilities."""

from pathlib import Path

import pytest
from tests.fixtures.synthetic_bu import write_synthetic_bu_file

from election_research.core.exceptions import DataSourceError
from election_research.ingestion.csv_reader import (
    detect_delimiter,
    detect_encoding,
    inspect_csv_file,
    inspect_directory_files,
)


def test_detect_encoding_and_delimiter(tmp_path: Path):
    csv_file = tmp_path / "sample.csv"
    write_synthetic_bu_file(csv_file, ano=2026, turno=1, uf="RR")

    encoding = detect_encoding(csv_file)
    assert encoding in ("iso-8859-1", "cp1252", "latin1")

    delimiter = detect_delimiter(csv_file, encoding=encoding)
    assert delimiter == ";"


def test_inspect_csv_file(tmp_path: Path):
    csv_file = tmp_path / "sample.csv"
    write_synthetic_bu_file(csv_file, ano=2026, turno=2, uf="AC", secoes=[101])

    result = inspect_csv_file(csv_file)
    assert result.column_count == 45
    assert result.delimiter == ";"
    assert "DT_GERACAO" in result.columns
    assert "QT_VOTOS" in result.columns
    assert result.sample_row["SG_UF"] == "AC"
    assert result.sample_row["NR_TURNO"] == "2"


def test_inspect_nonexistent_file():
    with pytest.raises(DataSourceError, match="Target is not a valid file"):
        inspect_csv_file(Path("/nonexistent/file.csv"))


def test_inspect_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(DataSourceError, match="Empty CSV file"):
        inspect_csv_file(empty)


def test_inspect_directory_files(tmp_path: Path):
    dir_path = tmp_path / "round"
    write_synthetic_bu_file(dir_path / "file1.csv", uf="AC")
    write_synthetic_bu_file(dir_path / "file2.csv", uf="AL")

    results = inspect_directory_files(dir_path)
    assert len(results) == 2
    assert {r.sample_row["SG_UF"] for r in results} == {"AC", "AL"}
