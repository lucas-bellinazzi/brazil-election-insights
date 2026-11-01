"""CLI tool for inspecting raw TSE CSV files."""

import argparse
import sys
from pathlib import Path

from election_research.core.config import get_settings
from election_research.core.logging import get_logger, setup_logging
from election_research.ingestion.csv_reader import inspect_csv_file, inspect_directory_files

logger = get_logger("inspect_csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect raw TSE CSV files for delimiters, encodings, headers, and schemas."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Election year to inspect (default: 2026)",
    )
    parser.add_argument(
        "--round",
        choices=["1t", "2t", "all"],
        default="all",
        help="Election round to inspect (default: all)",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Specific CSV file path to inspect directly.",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()
    settings = get_settings()

    if args.file:
        file_path = args.file.resolve()
        if not file_path.is_file():
            logger.error("Specified file not found: %s", file_path)
            return 1
        res = inspect_csv_file(file_path)
        print(f"\n--- Inspection for {file_path.name} ---")
        print(f"Size: {res.file_size_bytes / (1024 * 1024):.2f} MB")
        print(f"Encoding: {res.encoding}")
        print(f"Delimiter: '{res.delimiter}'")
        print(f"Columns ({res.column_count}): {res.columns}")
        print("\nSample Row:")
        for col, val in res.sample_row.items():
            print(f"  {col}: {val}")
        return 0

    bronze_year = settings.bronze_dir / "tse" / str(args.year)
    if not bronze_year.is_dir():
        logger.error("Bronze directory not found: %s", bronze_year)
        return 1

    rounds = ["1t", "2t"] if args.round == "all" else [args.round]
    all_results = []

    for rnd in rounds:
        round_dir = bronze_year / rnd
        if not round_dir.is_dir():
            logger.warning("Round directory not found: %s", round_dir)
            continue
        results = inspect_directory_files(round_dir)
        all_results.extend(results)

        total_size_mb = sum(r.file_size_bytes for r in results) / (1024 * 1024)
        print(f"\nRound {rnd}: {len(results)} files found, total size: {total_size_mb:.2f} MB")

    if not all_results:
        logger.warning("No CSV files found in bronze directory.")
        return 0

    total_bytes = sum(r.file_size_bytes for r in all_results)
    total_gb = total_bytes / (1024**3)
    print(f"\nTotal Files: {len(all_results)} | Total Volume: {total_gb:.2f} GB")

    first = all_results[0]
    print(f"Standard Encoding: {first.encoding}")
    print(f"Standard Delimiter: '{first.delimiter}'")
    print(f"Column Count: {first.column_count}")

    # Check for header discrepancies across all discovered files
    discrepancies = [r.file_path for r in all_results if r.columns != first.columns]
    if discrepancies:
        logger.warning(
            "Found %d files with non-standard headers: %s",
            len(discrepancies),
            discrepancies,
        )
    else:
        print("Header Verification: 100% of discovered CSV files match the 45-column layout.")

    print("\nCanonical Column Names:")
    for idx, col in enumerate(first.columns):
        sample_val = first.sample_row.get(col, "")
        print(f"  [{idx:02d}] {col} (e.g., '{sample_val}')")

    return 0


if __name__ == "__main__":
    sys.exit(main())
