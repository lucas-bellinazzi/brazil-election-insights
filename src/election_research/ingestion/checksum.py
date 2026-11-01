"""Cryptographic integrity and checksum utilities for Bronze raw files."""

import hashlib
from pathlib import Path

from election_research.core.exceptions import DataIntegrityError, DataSourceError
from election_research.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MB stream chunks


def calculate_sha512(file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE) -> str:
    """Calculate the SHA-512 hash of a file using chunked streaming."""
    if not file_path.is_file():
        raise DataSourceError(f"File not found: {file_path}")

    hasher = hashlib.sha512()
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def verify_file_checksum(
    file_path: Path,
    expected_hash: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> bool:
    """Verify that a file's SHA-512 matches the expected hash."""
    calculated = calculate_sha512(file_path, chunk_size=chunk_size)
    matches = calculated == expected_hash.strip().lower()
    if not matches:
        logger.warning(
            "Integrity failure for %s: expected %s, got %s",
            file_path.name,
            expected_hash,
            calculated,
        )
    return matches


def read_official_sha512(checksum_file: Path) -> str:
    """Read expected hash from an official .sha512 file."""
    if not checksum_file.is_file():
        raise DataSourceError(f"Checksum file not found: {checksum_file}")

    content = checksum_file.read_text(encoding="utf-8").strip()
    # Typical formats: '<hash>  filename' or just '<hash>'
    parts = content.split()
    if not parts:
        raise DataIntegrityError(f"Empty checksum file: {checksum_file}")

    hash_candidate = parts[0].strip().lower()
    # Must contain valid hexadecimal characters
    if not all(c in "0123456789abcdef" for c in hash_candidate):
        raise DataIntegrityError(
            f"Invalid SHA-512 format in {checksum_file.name}: expected hex digits."
        )

    return hash_candidate
