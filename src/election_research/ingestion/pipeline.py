"""Idempotent batch and streaming data ingestion pipeline from Bronze to Silver."""

import json
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from election_research.core.config import get_settings
from election_research.core.logging import get_logger
from election_research.data.normalizer import normalize_bu_dataframe
from election_research.data.schemas import RAW_CSV_SCHEMA_OVERRIDES
from election_research.data.transformer import transform_to_silver_tables, write_silver_parquet
from election_research.data.validator import validate_silver_data
from election_research.ingestion.file_discovery import discover_bronze_files

logger = get_logger("ingestion_pipeline")


@dataclass
class FileIngestionStats:
    file_name: str
    uf: str
    election_round: str
    raw_rows: int
    valid_rows: int
    rejected_rows: int
    duration_seconds: float
    status: str
    error_message: str | None = None


@dataclass
class IngestionPipelineReport:
    pipeline_version: str = "1.0"
    year: int = 2026
    election_round: str = "all"
    started_at: str = ""
    completed_at: str = ""
    total_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    total_raw_rows: int = 0
    total_valid_rows: int = 0
    total_rejected_rows: int = 0
    total_duration_seconds: float = 0.0
    file_details: list[FileIngestionStats] = None  # type: ignore[assignment]

    def to_dict(self) -> dict:
        return asdict(self)


def ingest_single_file(
    file_path: Path, year: int, election_round: str, uf: str
) -> FileIngestionStats:
    """Process an individual Bronze CSV file into Silver Parquet tables."""
    start = time.time()
    settings = get_settings()

    try:
        # Read CSV with Latin-1 encoding, semicolon delimiter, and explicit text overrides
        raw_df = pl.read_csv(
            file_path,
            separator=";",
            encoding="iso-8859-1",
            null_values=["#NULO#"],
            schema_overrides=RAW_CSV_SCHEMA_OVERRIDES,
            truncate_ragged_lines=True,
        )
        raw_rows = len(raw_df)

        # Normalize
        normalized_df = normalize_bu_dataframe(raw_df, source_file=file_path)

        # Validate
        valid_df, rejected_df, val_report = validate_silver_data(normalized_df)

        # Save rejected records if any
        if len(rejected_df) > 0:
            quarantine_dir = settings.processing_history_dir / "quarantine" / str(year)
            quarantine_dir.mkdir(parents=True, exist_ok=True)
            quarantine_file = quarantine_dir / f"rejected_{file_path.stem}.parquet"
            rejected_df.write_parquet(quarantine_file)
            logger.warning("Saved %d rejected rows to %s", len(rejected_df), quarantine_file)

        # Transform to Silver entities
        silver_tables = transform_to_silver_tables(valid_df)

        # Write Silver Parquet partitioned
        write_silver_parquet(
            silver_tables,
            silver_dir=settings.silver_dir,
            year=year,
            election_round=election_round,
            uf=uf,
        )

        duration = time.time() - start
        return FileIngestionStats(
            file_name=file_path.name,
            uf=uf,
            election_round=election_round,
            raw_rows=raw_rows,
            valid_rows=val_report.valid_records,
            rejected_rows=val_report.rejected_records,
            duration_seconds=duration,
            status="SUCCESS",
        )
    except Exception as e:
        duration = time.time() - start
        logger.error("Failed to ingest %s: %s", file_path.name, e, exc_info=True)
        return FileIngestionStats(
            file_name=file_path.name,
            uf=uf,
            election_round=election_round,
            raw_rows=0,
            valid_rows=0,
            rejected_rows=0,
            duration_seconds=duration,
            status="FAILED",
            error_message=str(e),
        )


def run_ingestion(
    year: int = 2026,
    election_round: str = "all",
    uf: str | None = None,
    limit_files: int | None = None,
) -> IngestionPipelineReport:
    """Execute end-to-end Bronze-to-Silver ingestion."""
    settings = get_settings()
    settings.ensure_directories()
    start_time = time.time()
    started_iso = datetime.now(UTC).isoformat()

    discovered = discover_bronze_files(
        bronze_dir=settings.bronze_dir,
        year=year,
        election_round=election_round,
        uf=uf,
    )

    if limit_files and limit_files > 0:
        discovered = discovered[:limit_files]

    logger.info(
        "Discovered %d file(s) for ingestion (Year: %d, Round: %s, UF: %s)",
        len(discovered),
        year,
        election_round,
        uf or "ALL",
    )

    file_stats: list[FileIngestionStats] = []
    for idx, f_info in enumerate(discovered, 1):
        mb_size = f_info.size_bytes / (1024 * 1024)
        print(
            f"[{idx:02d}/{len(discovered):02d}] Ingesting {f_info.file_name} ({mb_size:.1f} MB)...",
            end=" ",
            flush=True,
        )
        stats = ingest_single_file(
            file_path=f_info.file_path,
            year=f_info.year,
            election_round=f_info.election_round,
            uf=f_info.uf,
        )
        file_stats.append(stats)
        if stats.status == "SUCCESS":
            print(f"DONE ({stats.valid_rows:,} rows in {stats.duration_seconds:.2f}s)")
        else:
            print(f"FAILED: {stats.error_message}")

    total_duration = time.time() - start_time
    completed_iso = datetime.now(UTC).isoformat()

    report = IngestionPipelineReport(
        year=year,
        election_round=election_round,
        started_at=started_iso,
        completed_at=completed_iso,
        total_files=len(file_stats),
        successful_files=sum(1 for s in file_stats if s.status == "SUCCESS"),
        failed_files=sum(1 for s in file_stats if s.status == "FAILED"),
        total_raw_rows=sum(s.raw_rows for s in file_stats),
        total_valid_rows=sum(s.valid_rows for s in file_stats),
        total_rejected_rows=sum(s.rejected_rows for s in file_stats),
        total_duration_seconds=total_duration,
        file_details=file_stats,
    )

    # Save execution audit history
    history_file = settings.processing_history_dir / f"ingestion_{year}_{int(time.time())}.json"
    history_file.parent.mkdir(parents=True, exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    logger.info("Saved ingestion history log to %s", history_file)
    print(
        f"\nIngestion Complete: {report.successful_files}/{report.total_files} succeeded | "
        f"{report.total_valid_rows:,} valid rows generated in {total_duration:.1f}s."
    )
    return report
