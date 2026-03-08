class ConfigurationError(Exception):
    """Raised when required configuration (e.g., DATABASE_URL) is missing."""


class DatabaseError(Exception):
    """Raised for database connectivity or operation failures."""
