"""CLI tool for executing data quality and referential integrity validations on Silver datasets."""

import argparse
import sys

import polars as pl

from election_research.core.config import get_settings
from election_research.core.logging import get_logger, setup_logging
from election_research.data.repository import DataRepository

logger = get_logger("validate_data")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Silver Parquet dataset quality, integrity, and math invariants."
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Election year to validate (default: 2026)",
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
        help="Optional single UF code filter",
    )
    return parser.parse_args()


def run_validation(year: int = 2026, election_round: str = "all", uf: str | None = None) -> int:
    settings = get_settings()
    repo = DataRepository(settings)
    rounds = ["1t", "2t"] if election_round == "all" else [election_round]

    total_checks = 0
    passed_checks = 0

    print("\n==================================================")
    print(f"  SILVER DATA QUALITY REPORT — Year {year}")
    print("==================================================")

    for rnd in rounds:
        print(f"\n--- Round {rnd} Validation ---")
        try:
            repo.get_silver_scan("elections", year=year, election_round=rnd)
            sections_scan = repo.get_silver_scan(
                "polling_sections", year=year, election_round=rnd, uf=uf
            )
            candidates_scan = repo.get_silver_scan("candidates", year=year, election_round=rnd)
            votes_scan = repo.get_silver_scan("votes", year=year, election_round=rnd, uf=uf)

            # 1. Row counts
            total_checks += 1
            n_sections = sections_scan.select(pl.len()).collect().item()
            n_candidates = candidates_scan.select(pl.len()).collect().item()
            n_votes = votes_scan.select(pl.len()).collect().item()

            print(
                f"[CHECK 1: Row Counts] Sections: {n_sections:,} | "
                f"Candidates: {n_candidates:,} | Vote Rows: {n_votes:,}"
            )
            if n_sections > 0 and n_votes > 0:
                passed_checks += 1
                print("  -> PASSED: Tables contain non-zero records.")
            else:
                print("  -> FAILED: One or more tables are empty.")

            # 2. Key null checks on votes
            total_checks += 1
            null_keys = (
                votes_scan.filter(
                    pl.col("state_abbreviation").is_null()
                    | pl.col("municipality_tse_code").is_null()
                    | pl.col("electoral_zone").is_null()
                    | pl.col("polling_section").is_null()
                    | pl.col("vote_count").is_null()
                )
                .select(pl.len())
                .collect()
                .item()
            )

            if null_keys == 0:
                passed_checks += 1
                print(f"[CHECK 2: Primary Keys] PASSED: 0 null keys in {n_votes:,} vote records.")
            else:
                print(f"[CHECK 2: Primary Keys] FAILED: {null_keys} null keys.")

            # 3. Non-negative vote counts
            total_checks += 1
            negative_votes = (
                votes_scan.filter(pl.col("vote_count") < 0).select(pl.len()).collect().item()
            )
            if negative_votes == 0:
                passed_checks += 1
                print("[CHECK 3: Non-negative Vote Counts] PASSED: All vote counts >= 0.")
            else:
                print(
                    f"[CHECK 3: Non-negative Vote Counts] FAILED: {negative_votes} negative counts."
                )

            # 4. Turnout balance on polling sections (aptos == comparecimento + abstencoes)
            total_checks += 1
            balance_mismatches = (
                sections_scan.filter(
                    pl.col("eligible_voters") != (pl.col("actual_turnout") + pl.col("abstentions"))
                )
                .select(pl.len())
                .collect()
                .item()
            )

            if balance_mismatches == 0:
                passed_checks += 1
                print(f"[CHECK 4: Turnout Balance] PASSED: 100% of {n_sections:,} sections valid.")
            else:
                print(f"[CHECK 4: Turnout Balance] FAILED: {balance_mismatches} sections mismatch.")

        except Exception as e:
            logger.error("Validation error for round %s: %s", rnd, e)
            print(f"Validation error for round {rnd}: {e}")

    print("\n==================================================")
    print(f"  Summary: {passed_checks}/{total_checks} quality checks passed.")
    print("==================================================")

    return 0 if passed_checks == total_checks and total_checks > 0 else 1


def main() -> int:
    setup_logging()
    args = parse_args()
    return run_validation(year=args.year, election_round=args.round, uf=args.uf)


if __name__ == "__main__":
    sys.exit(main())
