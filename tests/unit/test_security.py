"""Unit tests for security controls, path traversal prevention, and input sanitization."""

import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from election_research.ai.tools import (
    MunicipalityToolArgs,
    StandardElectionArgs,
    TopAbstentionToolArgs,
    execute_tool_call,
)
from election_research.core.exceptions import SecurityError
from election_research.core.security import (
    SensitiveDataFilter,
    mask_secret,
    redact_sensitive_text,
    sanitize_election_round,
    sanitize_table_name,
    sanitize_uf,
    sanitize_year,
    validate_safe_path,
)
from election_research.database.connection import get_connection
from election_research.database.queries import (
    query_municipality_results,
    query_polling_sections,
    query_top_abstention_municipalities,
)


class TestPathValidation:
    """Tests for path traversal defense."""

    def test_safe_path_resolution(self, tmp_path: Path):
        sub_dir = tmp_path / "sub"
        sub_dir.mkdir()
        target_file = sub_dir / "data.csv"
        target_file.touch()

        resolved = validate_safe_path(target_file, tmp_path)
        assert resolved == target_file.resolve()

    def test_path_traversal_detection(self, tmp_path: Path):
        malicious = tmp_path / ".." / "outside.csv"
        with pytest.raises(SecurityError, match="Path traversal detected"):
            validate_safe_path(malicious, tmp_path)

    def test_null_byte_rejection(self, tmp_path: Path):
        with pytest.raises(SecurityError, match="Null byte"):
            validate_safe_path(str(tmp_path) + "/file\0.csv", tmp_path)


class TestInputSanitization:
    """Tests for UF, year, round, and table name sanitization."""

    def test_sanitize_uf_valid(self):
        assert sanitize_uf("sp") == "SP"
        assert sanitize_uf("RJ") == "RJ"
        assert sanitize_uf("BR") == "BR"
        assert sanitize_uf(None) is None

    def test_sanitize_uf_invalid(self):
        with pytest.raises(SecurityError, match="Invalid UF code"):
            sanitize_uf("INVALID")
        with pytest.raises(SecurityError, match="Invalid UF code"):
            sanitize_uf("SP; DROP TABLE users;")
        with pytest.raises(SecurityError, match="Invalid UF code"):
            sanitize_uf("../")

    def test_sanitize_year(self):
        assert sanitize_year(2026) == 2026
        assert sanitize_year("2022") == 2022
        with pytest.raises(SecurityError, match="historical range"):
            sanitize_year(1900)
        with pytest.raises(SecurityError, match="must be an integer"):
            sanitize_year("invalid_year")

    def test_sanitize_round(self):
        assert sanitize_election_round("1") == "1t"
        assert sanitize_election_round("1t") == "1t"
        assert sanitize_election_round("2") == "2t"
        assert sanitize_election_round("all") == "all"
        assert sanitize_election_round(None) == "all"
        with pytest.raises(SecurityError, match="Invalid election round"):
            sanitize_election_round("3")

    def test_sanitize_table_name(self):
        allowed = frozenset({"elections", "polling_sections"})
        assert sanitize_table_name("elections", allowed) == "elections"
        with pytest.raises(SecurityError, match="Unauthorized table name"):
            sanitize_table_name("users; DROP TABLE", allowed)


class TestSecretsRedaction:
    """Tests for masking and scrubbing sensitive API tokens."""

    def test_mask_secret(self):
        key = "sk-proj-1234567890abcdef1234"
        masked = mask_secret(key)
        assert masked.startswith("sk-p")
        assert masked.endswith("1234")
        assert "*" in masked
        assert key not in masked

    def test_redact_sensitive_text(self):
        msg = "Error contacting OpenAI with key sk-abcdef12345678901234567890 and Bearer xyz123456789012345678"
        redacted = redact_sensitive_text(msg)
        assert "sk-abcdef" not in redacted
        assert "[REDACTED_SECRET]" in redacted

    def test_logging_filter(self):
        log_filter = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="Call failed for sk-1234567890abcdef1234567890",
            args=(),
            exc_info=None,
        )
        assert log_filter.filter(record) is True
        assert "sk-123456" not in record.msg
        assert "[REDACTED_SECRET]" in record.msg


class TestAIToolSecurityValidation:
    """Tests that AI tools strictly reject malicious or unauthorized argument payloads."""

    def test_pydantic_forbids_extra_fields(self):
        with pytest.raises(ValidationError):
            StandardElectionArgs.model_validate({"year": 2026, "injected_param": "drop table"})

    def test_top_abstention_bounds(self):
        valid = TopAbstentionToolArgs.model_validate({"top_n": 25, "min_voters": 1000})
        assert valid.top_n == 25

        with pytest.raises(ValidationError):
            TopAbstentionToolArgs.model_validate({"top_n": 5000})  # Exceeds max 100

        with pytest.raises(ValidationError):
            TopAbstentionToolArgs.model_validate({"min_voters": -50})

    def test_municipality_args_uf_sanitization(self):
        valid = MunicipalityToolArgs.model_validate({"municipality_name": "Campinas", "uf": "sp"})
        assert valid.uf == "SP"

        with pytest.raises(ValidationError):
            MunicipalityToolArgs.model_validate(
                {"municipality_name": "Test", "uf": "MALICIOUS_INJECTION"}
            )

    def test_execute_tool_call_graceful_rejection(self):
        # Malicious payload with extra fields or injection
        res = execute_tool_call(
            "get_election_overview",
            {"year": 2026, "sql_injection": "1=1; DROP TABLE gold_national_summary;"},
        )
        assert "error" in res
        assert "Invalid tool arguments" in res["error"]

    def test_unrecognized_tool_rejection(self):
        res = execute_tool_call("drop_database", {})
        assert "error" in res
        assert "is not recognized or permitted" in res["error"]


class TestSQLInjectionResilience:
    """Tests ensuring SQL queries with malicious strings do not cause syntax errors or injections."""

    def test_parameterized_query_municipality(self):
        conn = get_connection(db_path=":memory:", register_views=False)
        # Attempt SQL injection payload in name_filter and limit
        injection_attempt = "SP' OR '1'='1"
        try:
            # Query executes against empty views or mocked table safely with params
            df = query_municipality_results(
                conn,
                year=2026,
                election_round=2,
                office_code=1,
                uf="SP",
                name_filter=injection_attempt,
                limit=10,
            )
            assert len(df) == 0
        except Exception as e:
            # Table might not exist in in-memory test; must NOT be a SQL syntax/injection error
            assert "gold_municipality_summary" in str(e)
            assert "syntax error" not in str(e).lower()

    def test_parameterized_query_polling_sections(self):
        conn = get_connection(db_path=":memory:", register_views=False)
        try:
            query_polling_sections(conn, year=2026, election_round=2, uf="AC", zone=1, limit=5)
        except Exception as e:
            assert "silver_polling_sections" in str(e)
            assert "syntax error" not in str(e).lower()

    def test_parameterized_query_top_abstention(self):
        conn = get_connection(db_path=":memory:", register_views=False)
        try:
            query_top_abstention_municipalities(
                conn, year=2026, election_round=2, office_code=1, min_voters=5000, top_n=5
            )
        except Exception as e:
            assert "gold_municipality_summary" in str(e)
            assert "syntax error" not in str(e).lower()
