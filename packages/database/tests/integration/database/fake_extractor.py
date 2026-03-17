"""Shared fake extractor for integration testing."""

from nl_processing.database.detailed_models import DetailedWordRecord


class FakeExtractor:
    """Mock extractor for integration testing."""

    def __init__(self, results: list[DetailedWordRecord]) -> None:
        self.extract_calls: list = []
        self._results = results

    async def extract(self, words: list) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results
