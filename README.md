# Brazil Election Insights

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/badge/package%20manager-uv-green.svg)](https://docs.astral.sh/uv/)
[![DuckDB](https://img.shields.io/badge/database-DuckDB-yellow.svg)](https://duckdb.org/)
[![Streamlit](https://img.shields.io/badge/ui-Streamlit-red.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An open-source analytical platform for the exploration, investigation, and statistical analysis of Brazilian electoral data published by the **Tribunal Superior Eleitoral (TSE)**, with particular emphasis on **Boletins de Urna (BUs)**.

---

## Key Features

- **Medallion Data Architecture**:
  - **Bronze**: Raw TSE CSV files preserved without modification, validated via SHA-512 cryptographic manifests.
  - **Silver**: Normalized, typed, referentially validated Parquet tables (`elections`, `polling_sections`, `candidates`, `votes`).
  - **Gold**: High-performance analytical aggregates (`national_summary`, `state_summary`, `municipality_summary`, `candidate_summary`).
- **High-Performance Analytics**: Zero-copy SQL querying via DuckDB over columnar Apache Parquet datasets.
- **Statistical Rigor & Anomaly Detection**:
  - Parametric Z-Score, Non-parametric IQR, and Multivariate Isolation Forest.
  - Strict neutrality protocol: statistical signals are treated as hypotheses for empirical inquiry, **never** as proof of electoral fraud.
- **AI Assistant with Allowlisted Tools**: Grounded in deterministic DuckDB queries using function calling without arbitrary SQL or Python execution.
- **Interactive Multi-Page Streamlit UI**:
  - `01_Overview.py`: Consolidated national indicators, candidate rankings, and state comparisons.
  - `02_Data_Explorer.py`: Drill-down by municipality, electoral zone, and individual voting urns.
  - `03_Statistical_Analysis.py`: Distribution histograms, boxplots, and anomaly signals.
  - `04_Closing_Times.py`: Temporal flow of polling station closures, 2-hour exceptional extension, territorial disparities, and candidate correlations.
  - `05_AI_Assistant.py`: Interactive conversational assistant powered by Hugging Face (Qwen3.5-4B) and allowlisted deterministic tools.
  - `06_Methodology.py`: Transparent documentation of sources, invariant identities, and ethics.
- **Automated Reporting**: One-command reproducible markdown and JSON analytical reports.

---

## Quick Start

### 1. Requirements & Setup

```bash
# Clone the repository
git clone https://github.com/your-username/brazil-election-insights.git
cd brazil-election-insights

# Install dependencies using uv
uv sync

# Setup environment variables
Copy-Item .env.example .env   # Windows
# or cp .env.example .env     # Linux / macOS
```

### 2. End-to-End Pipeline Execution

```bash
# 1. Inspect raw CSV files and verify 45-column layout
uv run python scripts/inspect_csv.py --round all

# 2. Compute SHA-512 hashes and generate Bronze manifests
uv run python scripts/calculate_checksums.py --round 2t

# 3. Ingest Bronze CSVs into partitioned Silver Parquet tables
uv run python scripts/ingest_data.py --round 2t

# 4. Run data quality and mathematical integrity checks
uv run python scripts/validate_data.py --round 2t

# 5. Generate Gold analytical summaries
uv run python scripts/generate_aggregations.py --round 2t

# 6. Generate automated analytical report
uv run python scripts/generate_report.py --round 2t
```

### 3. Launch the Interactive Dashboard

```bash
uv run streamlit run app/Home.py
```

Open your browser at `http://localhost:8501`.

---

## Testing & Code Quality

Run the automated test suite and linter checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

---

## Repository Structure

```
brazil-election-insights/
├── app/                        # Streamlit application
│   ├── Home.py                 # Landing page
│   ├── pages/                  # Multi-page dashboards
│   └── components/             # Reusable UI charts, tables, filters
├── src/election_research/      # Core Python package
│   ├── core/                   # Config, logging, exceptions
│   ├── ingestion/              # Checksum, discovery, manifests, pipeline
│   ├── data/                   # Normalizer, validator, transformer, repository
│   ├── analytics/              # Descriptive, anomalies, statistical tests
│   ├── ai/                     # Assistant, provider, tools, prompts
│   └── database/               # DuckDB connection and parameterized queries
├── data/                       # Medallion data lake (Bronze, Silver, Gold, Metadata)
├── docs/                       # Architecture, data dictionary, methodology guides
├── scripts/                    # CLI pipeline utilities
├── tests/                      # Unit & integration tests
└── reports/                    # Generated analytical reports
```

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
