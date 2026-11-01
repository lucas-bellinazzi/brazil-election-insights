# System Architecture — Brazil Election Insights

## 1. Architectural Overview

**Brazil Election Insights** is built upon a modular, decoupled architecture following the **Medallion Pattern** (Bronze, Silver, Gold). The presentation layer (Streamlit), analytics engine, analytical database (DuckDB), and artificial intelligence service (OpenAI Assistant) are cleanly separated.

```
┌─────────────────────────────────┐
│     BRONZE: Raw TSE Files       │ ── CSV (Latin-1, semicolon) + SHA-512 Manifests
│  (Read-only, 56 files, 30.2 GB) │
└─────────────────────────────────┘
                 │
                 ▼ (Polars Normalizer + Validator)
┌─────────────────────────────────┐
│     SILVER: Structured Data     │ ── Columnar Parquet
│  (Partitioned by Year/Round/UF) │    Tables: elections, polling_sections,
└─────────────────────────────────┘            candidates, votes
                 │
                 ▼ (Analytics Aggregations)
┌─────────────────────────────────┐
│      GOLD: Analytical Data      │ ── Columnar Parquet
│  (Summaries & Rolled-up KPIs)   │    Tables: national, state, municipality,
└─────────────────────────────────┘            candidate summaries
                 │
                 ▼ (Zero-Copy Views)
┌─────────────────────────────────┐
│       DUCKDB SQL ENGINE         │ ── Analytical SQL Queries over Parquet
└─────────────────────────────────┘
         │               │
         ▼               ▼
┌────────────────┐ ┌────────────────┐
│  STREAMLIT UI  │ │  AI ASSISTANT  │
│ (Interactive   │ │ (Allowlisted   │
│  Dashboards)   │ │  Tools Only)   │
└────────────────┘ └────────────────┘
```

---

## 2. Component Responsibilities

| Subsystem | Modules | Core Responsibility |
| :--- | :--- | :--- |
| **Core** | `core/config.py`, `core/logging.py`, `core/exceptions.py` | Typed settings via Pydantic, directory lifecycle, logging, domain exceptions. |
| **Ingestion** | `ingestion/file_discovery.py`, `ingestion/checksum.py`, `ingestion/manifest.py`, `ingestion/pipeline.py` | Raw file discovery, streaming SHA-512 calculation, manifest provenance, batch pipeline. |
| **Data Layer** | `data/schemas.py`, `data/normalizer.py`, `data/validator.py`, `data/transformer.py`, `data/repository.py` | Canonical schemas, string/sentinel normalization, turnout balance validation, Parquet persistence. |
| **Analytics Engine**| `analytics/descriptive.py`, `analytics/anomalies.py`, `analytics/statistical_tests.py` | Turnout, vote share, Z-score, IQR, Isolation Forest, KS tests, correlation. |
| **Database** | `database/connection.py`, `database/queries.py` | DuckDB connection lifecycle, automated Parquet views, parameterized analytical SQL. |
| **AI Integration** | `ai/provider.py`, `ai/assistant.py`, `ai/tools.py`, `ai/prompts.py` | OpenAI provider, allowlisted function calling, deterministic local fallback. |
| **Presentation** | `app/Home.py`, `app/pages/*`, `app/components/*` | Streamlit interactive research dashboards, Plotly charts, data filters, tables. |

---

## 3. Data Integrity & Provenance Guarantees

1. **Immutable Bronze**: Source CSV files are opened in read-only mode and never modified.
2. **Cryptographic Signatures**: SHA-512 hashes recorded in `data/metadata/manifests/manifest_{year}_{round}.json`.
3. **Turnout Identity Validation**: Every polling section record is strictly verified against the invariant:
   $$\text{eligible\_voters} = \text{actual\_turnout} + \text{abstentions}$$
   Records that fail are quarantined to `data/metadata/processing_history/quarantine/`.
4. **Controlled AI Execution**: AI Assistant operates under strict guardrails; it cannot execute arbitrary code or write operations. All figures must originate from allowlisted tools.
