from nl_processing.database_core.exceptions import ConfigurationError, DatabaseError

# Re-export for backward compatibility
__all__ = ["DatabaseError", "ConfigurationError", "WordNotFoundError"]


class WordNotFoundError(DatabaseError):
    """Raised when a delete targets a source_word_id not in the user's vocabulary (FM-5)."""
