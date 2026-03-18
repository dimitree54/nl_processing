"""Shared database configuration helpers."""

import os

from nl_processing.database_core.exceptions import ConfigurationError

_DATABASE_URL_MISSING = (
    "DATABASE_URL environment variable is required. "
    "Set it to your Neon PostgreSQL connection string. "
    "See: https://neon.tech/docs/connect/connect-from-any-app"
)


def read_database_url() -> str:
    """Read DATABASE_URL from environment, raising ConfigurationError if absent."""
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise ConfigurationError(_DATABASE_URL_MISSING) from exc
