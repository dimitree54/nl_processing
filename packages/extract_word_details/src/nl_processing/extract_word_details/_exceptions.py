"""Exception types for extract_word_details package.

These exceptions are locally defined to avoid circular dependencies
between packages. They mirror the exceptions in the database package.
"""


class SchemaVersionError(Exception):
    """Raised when a schema version is unknown or unsupported."""


class PayloadValidationError(Exception):
    """Raised when a payload fails Pydantic model validation."""
