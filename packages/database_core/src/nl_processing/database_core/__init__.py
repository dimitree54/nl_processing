"""Database Core Package - Public Interface.

This package provides the core database abstractions and implementations for
the nl_processing system, including backend interfaces, connection management,
and configuration utilities.
"""

from nl_processing.database_core._database_config import read_database_url
from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.exceptions import ConfigurationError, DatabaseError

__all__ = [
    "AbstractBackend",
    "NeonBackend",
    "read_database_url",
    "ConfigurationError",
    "DatabaseError",
]
