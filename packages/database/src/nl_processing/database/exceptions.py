"""Database-owned exception types."""

from nl_processing.database_core.exceptions import DatabaseError


class WordNotFoundError(DatabaseError):
    """Raised when a delete targets a source word outside the user's vocabulary."""


__all__ = ["WordNotFoundError"]
