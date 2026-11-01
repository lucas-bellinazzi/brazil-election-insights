"""CLI tool to generate and persist Gold layer analytical aggregations."""

import argparse
import sys
import time

from election_research.analytics.descriptive import (
    generate_gold_candidate_summary,
    generate_gold_municipality_summary,
    generate_gold_national_summary,
    generate_gold_state_summary,
    write_gold_parquet,
)
from election_research.core.config import get_settings
from election_research.core.logging import get_logger, setup_logging
from election_research.data.repository import DataRepository

logger = get_logger("generate_aggregations")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute Gold analytical aggregates (National, State, Muni, Candidate)."
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
        default="2t",
        help="Election round (default: 2t)",
    )
    return parser.parse_args()


def run_generate_aggregations(year: int = 2026, election_round: str = "2t") -> int:
    settings = get_settings()
    repo = DataRepository(settings)
    rounds = ["1t", "2t"] if election_round == "all" else [election_round]

    start = time.time()
    for rnd in rounds:
        print("\n==================================================")
        print(f"  GENERATING GOLD AGGREGATIONS — Year {year}, Round {rnd}")
        print("==================================================")

        try:
            # 1. National Summary
            print("1. Computing National Summary...", end=" ", flush=True)
            t0 = time.time()
            nat_df = generate_gold_national_summary(repo, year=year, election_round=rnd)
            write_gold_parquet(
                nat_df, settings.gold_dir, "national_summary", year=year, election_round=rnd
            )
            print(f"DONE ({len(nat_df)} rows in {time.time() - t0:.2f}s)")

            # 2. State Summary
            print("2. Computing State Summary...", end=" ", flush=True)
            t0 = time.time()
            state_df = generate_gold_state_summary(repo, year=year, election_round=rnd)
            write_gold_parquet(
                state_df, settings.gold_dir, "state_summary", year=year, election_round=rnd
            )
            print(f"DONE ({len(state_df)} rows in {time.time() - t0:.2f}s)")

            # 3. Municipality Summary
            print("3. Computing Municipality Summary...", end=" ", flush=True)
            t0 = time.time()
            muni_df = generate_gold_municipality_summary(repo, year=year, election_round=rnd)
            write_gold_parquet(
                muni_df, settings.gold_dir, "municipality_summary", year=year, election_round=rnd
            )
            print(f"DONE ({len(muni_df)} rows in {time.time() - t0:.2f}s)")

            # 4. Candidate Summary
            print("4. Computing Candidate Rankings & Shares...", end=" ", flush=True)
            t0 = time.time()
            cand_df = generate_gold_candidate_summary(repo, year=year, election_round=rnd)
            write_gold_parquet(
                cand_df, settings.gold_dir, "candidate_summary", year=year, election_round=rnd
            )
            print(f"DONE ({len(cand_df)} rows in {time.time() - t0:.2f}s)")

        except Exception as e:
            logger.error("Aggregation failed for Round %s: %s", rnd, e, exc_info=True)
            print(f"\nFAILED for Round {rnd}: {e}")
            return 1

    total_time = time.time() - start
    print(f"\nAll Gold aggregations generated successfully in {total_time:.2f}s.")
    return 0


def main() -> int:
    setup_logging()
    args = parse_args()
    return run_generate_aggregations(year=args.year, election_round=args.round)


if __name__ == "__main__":
    sys.exit(main())
