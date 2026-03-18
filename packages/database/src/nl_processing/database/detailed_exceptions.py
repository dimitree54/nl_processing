"""Exception classes for detailed word operations."""

from nl_processing.database_core.exceptions import DatabaseError


class SourceWordNotFoundError(DatabaseError):
    """Raised when a source word is not found in the canonical corpus."""


class SchemaVersionError(DatabaseError):
    """Raised when a persisted row has an unsupported schema version."""


class PayloadValidationError(DatabaseError):
    """Raised when a payload fails validation."""
