"""Protocols for remote detailed word store and schema checker."""

from typing import Protocol

from nl_processing.core.models import Word
from nl_processing.database.detailed_models import DetailedWordRecord


class RemoteDetailedWordStorePort(Protocol):
    """Protocol for remote detailed word store backend."""

    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Fetch detailed word records from remote store."""


class SchemaVersionChecker(Protocol):
    """Protocol for checking schema version compatibility."""

    def is_compatible(self, schema_key: str, schema_version: int) -> bool:
        """Check if a schema version is compatible with current registry."""
