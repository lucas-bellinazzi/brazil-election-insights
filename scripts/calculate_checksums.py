"""CLI tool for calculating and verifying local SHA-512 checksums and manifests."""

import argparse
import sys
import time
from datetime import UTC, datetime

from election_research.core.config import get_settings
from election_research.core.logging import get_logger, setup_logging
from election_research.ingestion.checksum import calculate_sha512, read_official_sha512
from election_research.ingestion.file_discovery import (
    discover_bronze_files,
    get_official_checksum_file,
)
from election_research.ingestion.manifest import BronzeManifest, ManifestFileEntry

logger = get_logger("calculate_checksums")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute and verify SHA-512 checksums for Bronze TSE CSV files."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Election year (default: 2026)",
    )
    parser.add_argument(
        "--round",
        choices=["1t", "2t", "all"],
        default="all",
        help="Election round (default: all)",
    )
    parser.add_argument(
        "--uf",
        type=str,
        default=None,
        help="Optional state code filter (e.g. AC, SP, ZZ)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing manifest against disk instead of regenerating.",
    )
    return parser.parse_args()


def run_calculate_checksums(
    year: int = 2026,
    election_round: str = "all",
    uf: str | None = None,
    verify_only: bool = False,
) -> int:
    settings = get_settings()
    settings.ensure_directories()
    rounds = ["1t", "2t"] if election_round == "all" else [election_round]

    for rnd in rounds:
        logger.info("Processing Year %d, Round %s (UF filter: %s)", year, rnd, uf or "ALL")
        manifest_path = settings.manifests_dir / f"manifest_{year}_{rnd}.json"

        if verify_only:
            if not manifest_path.is_file():
                logger.error("Manifest not found for verification: %s", manifest_path)
                return 1
            manifest = BronzeManifest.load(manifest_path)
            logger.info("Verifying %d entries in %s", len(manifest.files), manifest_path.name)
            mismatches = 0
            for entry in manifest.files:
                if uf and entry.uf != uf.upper():
                    continue
                file_full = settings.project_root / entry.relative_path
                if not file_full.is_file():
                    logger.error("Missing file listed in manifest: %s", file_full)
                    mismatches += 1
                    continue
                current_hash = calculate_sha512(file_full)
                if current_hash != entry.sha512:
                    logger.error(
                        "Checksum mismatch for %s: expected %s, got %s",
                        entry.file_name,
                        entry.sha512,
                        current_hash,
                    )
                    mismatches += 1
                else:
                    logger.debug("Verified: %s", entry.file_name)
            if mismatches == 0:
                print(f"Manifest verification successful: all checked files in {rnd} match hashes.")
            else:
                logger.error("Manifest verification failed with %d mismatch(es).", mismatches)
                return 1
            continue

        # Normal calculation and manifest generation
        files = discover_bronze_files(
            settings.bronze_dir,
            year=year,
            election_round=rnd,
            uf=uf,
        )
        if not files:
            logger.warning("No files found for Year %d, Round %s", year, rnd)
            continue

        manifest = BronzeManifest(year=year, election_round=rnd)
        start_time = time.time()
        print(f"\nCalculating SHA-512 hashes for {len(files)} file(s) in Round {rnd}...")

        for idx, f_info in enumerate(files, 1):
            file_start = time.time()
            sha512_hash = calculate_sha512(f_info.file_path)
            file_duration = time.time() - file_start

            rel_path = f_info.file_path.relative_to(settings.project_root).as_posix()
            official_chk = get_official_checksum_file(f_info.file_path)
            official_hash = None
            status = "no_reference"
            if official_chk:
                try:
                    official_hash = read_official_sha512(official_chk)
                    status = "verified" if sha512_hash == official_hash else "mismatch"
                except Exception as e:
                    logger.warning("Failed to parse official checksum %s: %s", official_chk, e)

            entry = ManifestFileEntry(
                file_name=f_info.file_name,
                relative_path=rel_path,
                year=year,
                election_round=rnd,
                uf=f_info.uf,
                size_bytes=f_info.size_bytes,
                sha512=sha512_hash,
                official_sha512=official_hash,
                integrity_status=status,
                calculated_at=datetime.now(UTC).isoformat(),
            )
            manifest.add_entry(entry)
            mb_size = f_info.size_bytes / (1024 * 1024)
            print(
                f"  [{idx:02d}/{len(files):02d}] {f_info.file_name} "
                f"({mb_size:.1f} MB) in {file_duration:.2f}s -> {sha512_hash[:16]}..."
            )

        manifest.save(manifest_path)
        total_duration = time.time() - start_time
        total_mb = manifest.total_bytes / (1024 * 1024)
        print(
            f"Round {rnd} manifest saved: {manifest.total_files} files, "
            f"{total_mb:.1f} MB in {total_duration:.1f}s."
        )

    return 0


def main() -> int:
    setup_logging()
    args = parse_args()
    return run_calculate_checksums(
        year=args.year,
        election_round=args.round,
        uf=args.uf,
        verify_only=args.verify,
    )


if __name__ == "__main__":
    sys.exit(main())
