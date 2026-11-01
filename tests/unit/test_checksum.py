"""Unit tests for checksum and integrity functions."""

import hashlib
from pathlib import Path

import pytest

from election_research.core.exceptions import DataSourceError
from election_research.ingestion.checksum import (
    calculate_sha512,
    read_official_sha512,
    verify_file_checksum,
)


def test_calculate_sha512(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    content = b"Brazil Election Insights Test Payload"
    test_file.write_bytes(content)

    expected = hashlib.sha512(content).hexdigest().lower()
    calculated = calculate_sha512(test_file)
    assert calculated == expected


def test_calculate_sha512_missing_file():
    with pytest.raises(DataSourceError, match="File not found"):
        calculate_sha512(Path("/nonexistent/file.bin"))


def test_verify_file_checksum(tmp_path: Path):
    test_file = tmp_path / "test.txt"
    content = b"Verifiable Content"
    test_file.write_bytes(content)
    real_hash = hashlib.sha512(content).hexdigest()

    assert verify_file_checksum(test_file, real_hash) is True
    assert verify_file_checksum(test_file, "wrong_hash_12345") is False


def test_read_official_sha512(tmp_path: Path):
    chk_file = tmp_path / "test.sha512"
    chk_file.write_text("a1b2c3d4e5f6  sample_file.csv\n", encoding="utf-8")

    parsed = read_official_sha512(chk_file)
    assert parsed == "a1b2c3d4e5f6"
