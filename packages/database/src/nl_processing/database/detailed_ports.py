"""Port protocols for detailed word extraction operations."""

from typing import Protocol, runtime_checkable

from nl_processing.core.models import Word

from nl_processing.database.detailed_models import DetailedWordRecord, JsonValue


@runtime_checkable
class DetailedWordExtractorPort(Protocol):
    """Protocol for extracting detailed word information from words."""

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]: ...


@runtime_checkable
class PayloadValidatorPort(Protocol):
    def validate_payload(self, schema_key: str, schema_version: int, payload: dict[str, JsonValue]) -> None:
        """Raise if payload is invalid for the given schema.

        Raises:
            SchemaVersionError: If schema_key/version is unknown.
            PayloadValidationError: If payload doesn't match the schema.
        """
        ...
