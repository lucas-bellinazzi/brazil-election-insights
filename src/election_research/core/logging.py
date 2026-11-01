"""Structured logging configuration for Brazil Election Insights."""

import logging
import sys

from election_research.core.config import get_settings
from election_research.core.security import SensitiveDataFilter

DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    level: str | None = None,
    log_format: str = DEFAULT_FORMAT,
) -> None:
    """Configure root logger with consistent formatting and specified log level."""
    if level is None:
        level = get_settings().log_level

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if already configured
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(numeric_level)
        handler.addFilter(SensitiveDataFilter())
        formatter = logging.Formatter(fmt=log_format, datefmt=DATE_FORMAT)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    else:
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
            handler.addFilter(SensitiveDataFilter())


def get_logger(name: str) -> logging.Logger:
    """Return a logger configured for the specified module name."""
    logger = logging.getLogger(name)
    if not logging.getLogger().handlers:
        setup_logging()
    return logger
