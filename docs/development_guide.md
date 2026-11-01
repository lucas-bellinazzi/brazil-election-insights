# Development Guide — Brazil Election Insights

## 1. Prerequisites

- Python 3.12+ (CPython)
- `uv` package manager (`https://docs.astral.sh/uv/`)
- Git

---

## 2. Environment Setup

Clone the repository and install all dependencies:

```bash
# Synchronize virtual environment with uv
uv sync

# Configure environment variables
Copy-Item .env.example .env   # On Windows PowerShell
# or cp .env.example .env     # On Linux / macOS
```

---

## 3. End-to-End Pipeline Execution

The data engineering and analytical pipeline can be executed completely via CLI scripts:

```bash
# 1. Inspect raw CSV layout, encoding, and header uniformity
uv run python scripts/inspect_csv.py --year 2026 --round all

# 2. Compute streaming SHA-512 checksums and generate Bronze manifests
uv run python scripts/calculate_checksums.py --year 2026 --round all

# Verify integrity against recorded manifest:
uv run python scripts/calculate_checksums.py --year 2026 --round 2t --verify

# 3. Ingest Bronze CSVs into partitioned Silver Parquet tables
uv run python scripts/ingest_data.py --year 2026 --round 2t

# Optional: ingest single UF for rapid development
uv run python scripts/ingest_data.py --year 2026 --round 2t --uf AC

# 4. Validate data quality and mathematical invariants
uv run python scripts/validate_data.py --year 2026 --round 2t

# 5. Generate Gold analytical summaries (National, State, Muni, Candidate)
uv run python scripts/generate_aggregations.py --year 2026 --round 2t

# 6. Generate automated analytical report (Markdown + KPIs)
uv run python scripts/generate_report.py --year 2026 --round 2t
```

---

## 4. Running the Streamlit Interface

Launch the interactive analytical platform:

```bash
uv run streamlit run app/Home.py
```

The application will start at `http://localhost:8501`.

---

## 5. Automated Testing & Code Quality

Run tests and linters before committing any changes:

```bash
# Run pytest test suite
uv run pytest

# Check code formatting and linting
uv run ruff check .
uv run ruff format --check .
```
