# Security & Supply Chain Architecture

## 1. Overview and Threat Model

The **Brazil Election Insights** analytical platform deals with critical public interest data from official Brazilian electoral authorities (Tribunal Superior Eleitoral - TSE). The platform enforces strict controls against:
1. **Supply chain attacks**: Malicious packages, dependency confusion, poisoned upstream releases, untrusted build hooks.
2. **Data tampering**: Modifications to raw Bronze TSE files, hash collisions, unverified inputs.
3. **Arbitrary code and SQL execution**: Path traversal, command injection, SQL injection in DuckDB.
4. **AI assistant exploitation**: Prompt injections, unauthorized function calls, sensitive data exfiltration.
5. **Denial of Service (DoS)**: Memory exhaustion, disk saturation, endless recursion or huge query allocations.

---

## 2. Supply Chain Security & Lockfile Policy

### 2.1 The Role of `uv.lock`
The `uv.lock` file is **NEVER disposable in production, continuous integration, or repository version control**.

- **Cryptographic Wheel Pinning**: Every dependency in `uv.lock` is pinned with its exact release version and the cryptographic SHA-256 hash of its wheel/sdist binary.
- **Defense Against Account Takeovers**: If an upstream PyPI package maintainer's account is compromised and an attacker uploads a trojanized release with the same or incremented version, an installation adhering to `uv.lock` **rejects the compromised package** because the SHA-256 hash does not match.
- **Scientific Reproducibility**: Prevents subtle numerical divergences in Polars, DuckDB, or SciPy calculations caused by silent upstream updates.
- **When is `uv.lock` modified?**: Only when a developer explicitly runs `uv lock --upgrade` or purposefully adds/removes dependencies, followed by automated security audits.

### 2.2 Dependency Auditing & Sandboxed Builds
- Modern build system `hatchling` is used exclusively. Legacy `setup.py` scripts that execute arbitrary Python code during installation are prohibited.
- `scripts/security_audit.py` performs automated checks to verify lockfile integrity and absence of untrusted package indices.

---

## 3. Defense-in-Depth Implementation

### 3.1 Path Traversal Defense (`validate_safe_path`)
- All user-supplied, dynamic, or discovered file paths are canonicalized via `.resolve()` and verified using `.relative_to(base_dir)`.
- Path traversal sequences (`../`, `..\`) and null-byte injections (`\0`) trigger a hard `SecurityError` and halt execution.
- Federation identifiers (`UF`) are restricted strictly to the 27 Brazilian state codes plus official TSE special locations (`BR`, `ZZ`, `VT`).

### 3.2 DuckDB Sandbox & Parameterized SQL
- **Extension Isolation**: Third-party community extensions and automatic extension downloads over the network are explicitly disabled (`allow_community_extensions=False`, `autoinstall_known_extensions=False`, `autoload_known_extensions=False`).
- **100% Parameterized Statements**: All queries in `src/election_research/database/queries.py` utilize parameterized `?` placeholders for both WHERE predicates and LIMIT clauses. String concatenation and f-string SQL assembly are prohibited.
- **Resource Constraints**: DuckDB connections are bounded to 4 execution threads (`PRAGMA threads=4`) and 4 GB RAM (`PRAGMA memory_limit='4GB'`).

### 3.3 AI Assistant & Tool Sandbox
- **No Direct Code Execution**: The AI assistant has zero ability to run raw SQL, Python `eval`, or shell commands.
- **Allowlisted Deterministic Tools**: The model is restricted to a catalog of 5 predefined analytical functions (`get_election_overview`, `get_candidate_rankings`, `get_state_results`, `get_top_abstention_municipalities`, `get_municipality_result`).
- **Strict Pydantic Validation**: All tool arguments are validated with `extra="forbid"`, regex patterns, and numerical bounds (`ge`, `le`). Payloads exceeding bounds or containing unexpected attributes are rejected immediately.

### 3.4 Secrets & API Key Protection
- **No Hardcoded Secrets**: Secrets and OpenAI API keys are loaded strictly from the environment or `.env`.
- **Log Scrubbing (`SensitiveDataFilter`)**: A custom logging filter intercepts and masks tokens matching regexes (`sk-...`, `Bearer ...`) before emitting logs to stdout or disk.
- **Version Control Exclusions**: `.gitignore` comprehensively ignores `.env`, `.env.*`, `*.duckdb`, and local database dumps.

---

## 4. Security Verification Commands

```bash
# 1. Run automated security test suite
uv run pytest tests/unit/test_security.py

# 2. Run repository security and supply chain audit script
uv run python scripts/security_audit.py

# 3. Verify linting and formatting
uv run ruff check .
uv run ruff format --check .
```

