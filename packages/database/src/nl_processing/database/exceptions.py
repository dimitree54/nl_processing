from nl_processing.database_core.exceptions import ConfigurationError, DatabaseError


class WordNotFoundError(DatabaseError):
    """Raised when a delete targets a source_word_id not in the user's vocabulary (FM-5)."""
