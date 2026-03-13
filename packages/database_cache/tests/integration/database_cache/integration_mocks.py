"""Mock classes for detailed cache integration tests."""

from nl_processing.core.models import Word
from nl_processing.database.detailed_models import DetailedWordRecord


class MockRemoteDetailedWordStore:
    """Mock remote detailed word store for integration testing."""

    def __init__(self, records: list[DetailedWordRecord] | None = None) -> None:
        self.records = records or []
        self.call_count = 0

    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
        """Mock implementation that tracks calls."""
        self.call_count += 1

        # Return records that match the requested words
        results = []
        for word in words:
            for record in self.records:
                if record.source_word == word.normalized_form and record.word_type == word.word_type.value:
                    results.append(record)
                    break

        return results


class MockSchemaChecker:
    """Mock schema version checker for integration testing."""

    def __init__(self, incompatible_versions: dict[str, list[int]] | None = None) -> None:
        self.incompatible_versions = incompatible_versions or {}

    def is_compatible(self, schema_key: str, schema_version: int) -> bool:
        """Mock implementation marking certain versions as incompatible."""
        if schema_key in self.incompatible_versions:
            return schema_version not in self.incompatible_versions[schema_key]
        return True
