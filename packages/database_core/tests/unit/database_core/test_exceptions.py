"""Unit tests for database_core exceptions."""

from typing import Never

import pytest

from nl_processing.database_core.exceptions import ConfigurationError, DatabaseError


def test_configuration_error_is_exception() -> None:
    """ConfigurationError should inherit from Exception."""
    assert issubclass(ConfigurationError, Exception)


def test_configuration_error_can_be_raised() -> Never:
    """ConfigurationError should be raisable with a message."""
    with pytest.raises(ConfigurationError, match="test message"):
        raise ConfigurationError("test message")


def test_database_error_is_exception() -> None:
    """DatabaseError should inherit from Exception."""
    assert issubclass(DatabaseError, Exception)


def test_database_error_can_be_raised() -> Never:
    """DatabaseError should be raisable with a message."""
    with pytest.raises(DatabaseError, match="test message"):
        raise DatabaseError("test message")


def test_exceptions_are_independent() -> None:
    """ConfigurationError and DatabaseError should be independent exception types."""
    assert not issubclass(ConfigurationError, DatabaseError)
    assert not issubclass(DatabaseError, ConfigurationError)
