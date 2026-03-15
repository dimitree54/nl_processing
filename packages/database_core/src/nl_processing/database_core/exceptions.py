class ConfigurationError(Exception):
    """Raised when required configuration is missing."""


class DatabaseError(Exception):
    """Raised for database connectivity or operation failures."""
