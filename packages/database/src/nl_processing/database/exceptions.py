class ConfigurationError(Exception):
    """Raised when required configuration (e.g., DATABASE_URL) is missing."""


class DatabaseError(Exception):
    """Raised for database connectivity or operation failures."""


class WordNotFoundError(DatabaseError):
    """Raised when a delete targets a source_word_id not in the user's vocabulary (FM-5)."""
