"""Core security controls, path validation, input sanitization, and secrets redaction."""

import logging
import re
from pathlib import Path

from election_research.core.exceptions import SecurityError

# Brazilian Federative Units + special TSE codes (ZZ = Abroad, VT = Transito, BR = Brasil)
VALID_UFS = frozenset(
    {
        "AC",
        "AL",
        "AM",
        "AP",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MG",
        "MS",
        "MT",
        "PA",
        "PB",
        "PE",
        "PI",
        "PR",
        "RJ",
        "RN",
        "RO",
        "RR",
        "RS",
        "SC",
        "SE",
        "SP",
        "TO",
        "ZZ",
        "VT",
        "BR",
    }
)

VALID_ROUNDS = frozenset({"1", "2", "1t", "2t", "all"})

# Regex for common secret patterns (OpenAI keys, bearer tokens, passwords)
SECRET_PATTERNS = [
    re.compile(r"(sk-[a-zA-Z0-9_\-]{20,})", re.IGNORECASE),
    re.compile(r"(Bearer\s+[a-zA-Z0-9_\-\.]{20,})", re.IGNORECASE),
    re.compile(r"(api[_\-]?key\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-]{16,})(['\"]?)", re.IGNORECASE),
]


def validate_safe_path(target: Path | str, base_dir: Path | str) -> Path:
    """Validate that target path resolves strictly inside base_dir without directory traversal."""
    if isinstance(target, str) and ("\0" in target or "\x00" in target):
        raise SecurityError("Null byte detected in file path.")

    try:
        base_resolved = Path(base_dir).resolve()
        target_resolved = Path(target).resolve()
    except Exception as e:
        raise SecurityError(f"Invalid path expression: {e}") from e

    try:
        # Raises ValueError if target_resolved is not relative to base_resolved
        target_resolved.relative_to(base_resolved)
    except ValueError as e:
        raise SecurityError(
            f"Path traversal detected: '{target}' resolves outside allowed directory '{base_dir}'"
        ) from e

    return target_resolved


def sanitize_uf(uf: str | None) -> str | None:
    """Sanitize and validate Brazilian UF code against standard federation identifiers."""
    if uf is None:
        return None

    cleaned = uf.strip().upper()
    if cleaned not in VALID_UFS:
        raise SecurityError(
            f"Invalid UF code '{uf}'. Must be a valid 2-letter Brazilian state code or 'BR'."
        )
    return cleaned


def sanitize_year(year: int) -> int:
    """Ensure election year falls within supported modern democratic era."""
    try:
        year_int = int(year)
    except (ValueError, TypeError) as e:
        raise SecurityError(f"Invalid election year '{year}': must be an integer.") from e

    if not (1988 <= year_int <= 2100):
        raise SecurityError(f"Year {year_int} is out of allowable historical range (1988 - 2100).")
    return year_int


def sanitize_election_round(rnd: str | int | None) -> str:
    """Validate and normalize election round representation."""
    if rnd is None or rnd == "" or rnd == "all":
        return "all"

    cleaned = str(rnd).strip().lower()
    if cleaned in ("1", "1t"):
        return "1t"
    if cleaned in ("2", "2t"):
        return "2t"

    raise SecurityError(f"Invalid election round '{rnd}'. Expected '1t', '2t', or 'all'.")


def sanitize_table_name(table_name: str, allowed_tables: set[str] | frozenset[str]) -> str:
    """Validate table or view name against a strict whitelist."""
    if not isinstance(table_name, str) or table_name not in allowed_tables:
        raise SecurityError(
            f"Unauthorized table name '{table_name}'. Permitted tables: {sorted(allowed_tables)}"
        )
    return table_name


def mask_secret(value: str | None, show_prefix: int = 4, show_suffix: int = 4) -> str:
    """Redact sensitive API token or secret string, preserving small prefix/suffix for debug."""
    if not value:
        return ""
    if len(value) <= (show_prefix + show_suffix):
        return "***"
    prefix = value[:show_prefix]
    suffix = value[-show_suffix:]
    masked_length = max(4, len(value) - show_prefix - show_suffix)
    return f"{prefix}{'*' * masked_length}{suffix}"


def redact_sensitive_text(text: str) -> str:
    """Scrub sensitive API tokens or bearer patterns from strings."""
    if not text:
        return ""
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("[REDACTED_SECRET]", result)
    return result


class SensitiveDataFilter(logging.Filter):
    """Logging filter that scrubs sensitive patterns from all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (redact_sensitive_text(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    redact_sensitive_text(v) if isinstance(v, str) else v for v in record.args
                )
        return True
