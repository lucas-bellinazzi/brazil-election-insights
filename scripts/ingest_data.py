"""CLI entrypoint for running the Bronze-to-Silver data ingestion pipeline."""

import argparse
import sys

from election_research.core.logging import setup_logging
from election_research.ingestion.pipeline import run_ingestion


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Bronze-to-Silver data ingestion pipeline into partitioned Parquet."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Election year to process (default: 2026)",
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
        help="Optional single UF code filter (e.g. AC, SP, ZZ)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files processed (for testing)",
    )
    return parser.parse_args()


def main() -> int:
    setup_logging()
    args = parse_args()
    report = run_ingestion(
        year=args.year,
        election_round=args.round,
        uf=args.uf,
        limit_files=args.limit,
    )
    return 1 if report.failed_files > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
