"""Custom domain exceptions for Brazil Election Insights."""


class ElectionResearchError(Exception):
    """Base exception for all domain-specific errors in Brazil Election Insights."""


class ConfigurationError(ElectionResearchError):
    """Raised when application configuration or environment variables are invalid."""


class DataSourceError(ElectionResearchError):
    """Raised when a data source file or directory cannot be found or read."""


class DataIntegrityError(ElectionResearchError):
    """Raised when data integrity checks (e.g. SHA-512 checksums) fail."""


class ValidationError(ElectionResearchError):
    """Raised when data fails schema validation or referential integrity constraints."""


class IngestionError(ElectionResearchError):
    """Raised during bronze ingestion failures."""


class TransformationError(ElectionResearchError):
    """Raised when transforming bronze data to silver representations fails."""


class AggregationError(ElectionResearchError):
    """Raised when calculating gold analytical aggregations fails."""


class DatabaseError(ElectionResearchError):
    """Raised when database connections or analytical queries fail."""


class AnalyticsError(ElectionResearchError):
    """Raised when statistical calculations or anomaly detection encounters an error."""


class AIProviderError(ElectionResearchError):
    """Raised when interactions with AI providers or tools encounter an error."""


class SecurityError(ElectionResearchError):
    """Raised when an operation violates security controls, bounds, or integrity boundaries."""
