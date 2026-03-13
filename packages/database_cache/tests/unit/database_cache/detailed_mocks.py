"""Mock classes for detailed cache unit tests."""

from nl_processing.core.models import Word
from nl_processing.database.detailed_models import DetailedWordRecord


class MockRemoteDetailedWordStore:
    """Mock remote detailed word store for testing."""

    def __init__(self, records: list[DetailedWordRecord] | None = None) -> None:
        self.records = records or []
        self.called_with: list[list[Word]] | None = None
        self.error_to_raise: Exception | None = None

    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Mock implementation of get_or_extract_details."""
        if self.error_to_raise is not None:
            raise self.error_to_raise

        self.called_with = [words] if self.called_with is None else self.called_with + [words]

        # Return records that match the requested words
        results = []
        for word in words:
            for record in self.records:
                if record.source_word == word.normalized_form and record.word_type == word.word_type.value:
                    results.append(record)
                    break

        return results


class MockSchemaChecker:
    """Mock schema version checker for testing."""

    def __init__(self, compatible_versions: dict[str, list[int]] | None = None) -> None:
        self.compatible_versions = compatible_versions or {}

    def is_compatible(self, schema_key: str, schema_version: int) -> bool:
        """Mock implementation of is_compatible."""
        if schema_key in self.compatible_versions:
            return schema_version in self.compatible_versions[schema_key]
        return True
