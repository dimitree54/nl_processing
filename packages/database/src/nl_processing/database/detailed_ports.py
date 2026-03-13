"""Port protocols for detailed word extraction operations."""

from typing import Protocol, runtime_checkable

from nl_processing.core.models import Word

from .detailed_models import DetailedWordRecord


@runtime_checkable
class DetailedWordExtractorPort(Protocol):
    """Protocol for extracting detailed word information from words."""

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]: ...
