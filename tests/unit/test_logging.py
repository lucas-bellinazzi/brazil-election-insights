"""Unit tests for structured logging."""

import logging

from election_research.core.logging import get_logger, setup_logging


def test_setup_logging_configures_level():
    setup_logging(level="DEBUG")
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    setup_logging(level="INFO")
    assert root_logger.level == logging.INFO


def test_get_logger_returns_named_logger():
    logger = get_logger("election_research.test")
    assert logger.name == "election_research.test"
    assert isinstance(logger, logging.Logger)
