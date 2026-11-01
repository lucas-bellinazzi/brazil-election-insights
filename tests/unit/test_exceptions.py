"""Unit tests for domain exception hierarchy."""

import pytest

from election_research.core.exceptions import (
    AIProviderError,
    AnalyticsError,
    ConfigurationError,
    DataIntegrityError,
    DataSourceError,
    ElectionResearchError,
    ValidationError,
)


def test_exception_inheritance():
    assert issubclass(ConfigurationError, ElectionResearchError)
    assert issubclass(DataSourceError, ElectionResearchError)
    assert issubclass(DataIntegrityError, ElectionResearchError)
    assert issubclass(ValidationError, ElectionResearchError)
    assert issubclass(AnalyticsError, ElectionResearchError)
    assert issubclass(AIProviderError, ElectionResearchError)


def test_exception_raising():
    with pytest.raises(DataIntegrityError, match="Checksum mismatch"):
        raise DataIntegrityError("Checksum mismatch")
