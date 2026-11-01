# AI Architecture & Integration — Hugging Face + Qwen3.5-4B

## 1. Executive Summary and Model Selection

The AI subsystem of **Brazil Election Insights** operates as an interactive, natural-language research assistant strictly grounded in official electoral data from the Tribunal Superior Eleitoral (TSE).

### Default Model
- **Repository**: [`Qwen/Qwen3.5-4B`](https://huggingface.co/Qwen/Qwen3.5-4B)
- **Model Family**: Qwen3.5
- **Parameters**: 4 Billion
- **License**: Apache 2.0
- **Format**: Safetensors
- **Primary Interaction Language**: Brazilian Portuguese (`pt-BR`)
- **Secondary Languages**: English (`en`), Spanish (`es`)

### Critical Principle: Non-Authoritative Computations
The language model is **never** responsible for calculating electoral statistics or guessing numerical values. All indicators, totals, rates, and rankings are calculated deterministically by DuckDB SQL queries over partitioned Parquet datasets and SciPy/scikit-learn statistical routines. The model acts strictly as an orchestrator: interpreting natural language intent, selecting approved analytical tools, and explaining structured findings.

---

## 2. Architecture Overview

```
                                 Streamlit UI
                                      │
                                      ▼
                             ElectionAIAssistant
                                      │
                                      ▼
                                ContextManager
                          (Sliding Window & Budget)
                                      │
                                      ▼
                                 AIProvider
                        (Common Provider Interface)
                                      │
               ┌──────────────────────┼──────────────────────┐
               ▼                      ▼                      ▼
            Mode A                 Mode B                 Mode C
         Serverless HF          Dedicated HF              Local
      Inference Providers    Inference Endpoints     vLLM / SGLang /
     (huggingface_hub)       (vLLM / TGI)            Transformers
               │                      │                      │
               └──────────────────────┼──────────────────────┘
                                      ▼
                                  Qwen3.5-4B
                           (Tool-Calling Decision)
                                      │
                                      ▼
                                 ToolRegistry
                         (Allowlisted 8 Tools & Schemas)
                                      │
                                      ▼
                                 ToolExecutor
                          (Pydantic Input Validation)
                                      │
                                      ▼
                            Analytical DuckDB Layer
                            (Parquet Gold / Silver)
                                      │
                                      ▼
                             Structured Results &
                            Provenancial Metadata
                                      │
                                      ▼
                                  Qwen3.5-4B
                           (Grounded Interpretation)
                                      │
                                      ▼
                             Final Explanation UI
```

---

## 3. Inference Strategies (Modes A, B, C)

All execution strategies implement the unified [`AIProvider`](file:///c:/Users/lucas/Documents/LUCAS/PROJECTS/brazil-election-insights/src/election_research/ai/provider.py) interface.

### Mode A — Hugging Face Serverless Inference Providers (`huggingface`)
- **Library**: `huggingface_hub.InferenceClient`
- **Use Case**: Default cloud serverless inference.
- **Authentication**: Requires `HF_TOKEN` in `.env`.
- **Capability Check**: Validates whether `Qwen/Qwen3.5-4B` has an active serverless provider. If unavailable, falls back gracefully without crashing.

### Mode B — Dedicated Inference Endpoints (`huggingface_endpoint`)
- **Configuration**: `HF_ENDPOINT_URL=https://<endpoint-id>.endpoints.huggingface.cloud`
- **Use Case**: High-throughput production deployments with dedicated GPU acceleration (e.g. Nvidia A10G / L4).
- **Runtime**: vLLM or SGLang container with OpenAI-compatible chat completion endpoints and native tool-calling parsers.
- **Smoke Test**: `health_check()` validates latency and readiness before queries are routed.

### Mode C — Local Development (`local`)
- **Options**:
  1. Local OpenAI-compatible server at `http://localhost:8000/v1` (vLLM, SGLang, llama-server).
  2. In-process Hugging Face `transformers` pipeline (`torch`, `transformers`, `accelerate`).
- **Optional Dependencies**: Installed via `uv sync --extra local-ai` to keep the core application lightweight.

---

## 4. The 8 Approved Analytical Tools

The model is strictly restricted to 8 validated analytical tools:

| Tool Name | Parameters | Target Dataset / Layer | Description |
|---|---|---|---|
| `get_national_summary` | `election_year`, `election_round` | Gold `national_summary` | National indicators: turnout, abstention, valid/blank/null votes, completeness. |
| `get_state_summary` | `state_code`, `election_year`, `election_round` | Gold `state_summary` | Consolidated indicators for an individual Brazilian state. |
| `get_municipality_summary` | `municipality_code`, `election_year`, `election_round` | Gold `municipality_summary` | Electoral indicators by TSE municipality code or name. |
| `get_candidate_results` | `candidate_id`, `election_year`, `election_round`, `geographic_filter` | Gold `candidate_summary` | Candidate ranking, ballot numbers, votes, and percentage shares. |
| `compare_geographic_results` | `geographic_level`, `geographic_identifiers`, `metric`, `election_year`, `election_round` | Gold state / municipality | Comparative analysis across multiple states or municipalities. |
| `get_abstention_analysis` | `geographic_level`, `geographic_identifier`, `election_year`, `election_round` | Gold summaries | Deep abstention rankings and distributions. |
| `detect_statistical_anomalies` | `geographic_level`, `geographic_identifier`, `metric`, `method`, `threshold`, `election_year`, `election_round` | Gold municipality & SciPy/sklearn | Outlier identification (Z-score, IQR, Isolation Forest) with mandatory neutral disclaimers. |
| `get_polling_section_details` | `state_code`, `polling_section_number`, `municipality_code`, `election_year`, `election_round` | Silver `polling_sections` | Raw Boletim de Urna (BU) indicators for an individual polling station. |

---

## 5. Security and Guardrails

1. **No Code or SQL Execution**: The model cannot execute raw SQL or Python code. There is no `execute_sql` or `run_script` tool.
2. **Pydantic Validation (`extra="forbid"`)**: Any extraneous or malicious parameters injected into tool calls cause immediate rejection.
3. **Reasoning Tag Scrubbing**: Qwen3.5 internal reasoning blocks (`<think>...</think>`) are parsed and removed by [`response_parser.py`](file:///c:/Users/lucas/Documents/LUCAS/PROJECTS/brazil-election-insights/src/election_research/ai/response_parser.py) and never presented to end users.
4. **Methodological Neutrality**: Outlier signals are returned with explicit disclaimers: *"Sinal estatístico atípico identificado para investigação empírica. Desvios estatísticos não constituem evidência ou prova de fraude eleitoral."*
5. **Deterministic Contingency**: If Hugging Face is unreachable or `AI_ENABLED=false`, all queries seamlessly execute deterministic DuckDB fallback lookups.

---

## 6. How-To Guide: Configuration & Deployment

### 6.1 Creating a Hugging Face Access Token
1. Create an account at [huggingface.co](https://huggingface.co).
2. Navigate to **Settings > Access Tokens**.
3. Create a **Fine-grained Token** with permissions:
   - `Inference`: "Make calls to the serverless Inference API"
   - `Inference Endpoints`: (Optional, if managing dedicated endpoints)
4. Copy the token and add it to `.env`:
   ```env
   HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

### 6.2 Environment Configuration (`.env`)
```env
AI_ENABLED=true
AI_PROVIDER=huggingface
AI_MODEL_ID=Qwen/Qwen3.5-4B

HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxx
HF_INFERENCE_PROVIDER=
HF_ENDPOINT_URL=

AI_TEMPERATURE=0.2
AI_MAX_NEW_TOKENS=2048
AI_REQUEST_TIMEOUT=120
AI_MAX_TOOL_ITERATIONS=5
AI_MAX_CONVERSATION_MESSAGES=12
AI_ENABLE_THINKING=false
```

### 6.3 Disabling AI
To operate purely in deterministic analytics mode without any external model calls:
```env
AI_ENABLED=false
```

### 6.4 Running Local Model Execution
To test with local GPU/CPU hardware:
```bash
# 1. Install optional local inference dependencies
uv sync --extra local-ai

# 2. Update .env
AI_PROVIDER=local
```
Or start a local vLLM server:
```bash
vllm serve Qwen/Qwen3.5-4B --port 8000
```
And set `AI_PROVIDER=local` with `HF_ENDPOINT_URL=http://localhost:8000/v1`.

### 6.5 Running Model Evaluation Benchmark
```bash
uv run python -c "from election_research.ai.evaluation import run_full_evaluation; print(run_full_evaluation().model_dump_json(indent=2))"
```

