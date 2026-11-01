"""Bronze manifest management and integrity provenance."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from election_research.core.exceptions import DataIntegrityError
from election_research.core.logging import get_logger

logger = get_logger(__name__)


class ManifestFileEntry(BaseModel):
    """Metadata and checksum record for a single bronze file."""

    file_name: str
    relative_path: str
    year: int
    election_round: str
    uf: str
    size_bytes: int
    sha512: str
    official_sha512: str | None = None
    integrity_status: Literal["verified", "no_reference", "mismatch"] = "no_reference"
    calculated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class BronzeManifest(BaseModel):
    """Manifest cataloging all verified Bronze input files for an election."""

    manifest_version: str = "1.0"
    year: int
    election_round: str
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    total_files: int = 0
    total_bytes: int = 0
    files: list[ManifestFileEntry] = Field(default_factory=list)

    def add_entry(self, entry: ManifestFileEntry) -> None:
        self.files.append(entry)
        self.total_files = len(self.files)
        self.total_bytes = sum(f.size_bytes for f in self.files)

    def save(self, target_path: Path) -> None:
        """Persist manifest to JSON atomically."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = target_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)
        temp_path.replace(target_path)
        logger.info("Saved manifest to %s (%d files)", target_path, self.total_files)

    @classmethod
    def load(cls, manifest_path: Path) -> "BronzeManifest":
        """Load manifest from JSON."""
        if not manifest_path.is_file():
            raise DataIntegrityError(f"Manifest not found: {manifest_path}")
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)
