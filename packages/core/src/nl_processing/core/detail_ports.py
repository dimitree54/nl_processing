"""Detail-related ports for cross-package contracts."""

from typing import Any, Protocol, runtime_checkable

from nl_processing.core.detail_models import DetailedWordRecord


@runtime_checkable
class DetailedWordRecordPort(Protocol):
    """Port for detailed word record retrieval."""

    async def get_details(self, *, words: list[str]) -> dict[str, DetailedWordRecord | None]: ...

    async def get_or_extract_details(self, *, words: list[str]) -> dict[str, DetailedWordRecord | None]: ...


@runtime_checkable
class WordExtractorPort(Protocol):
    """Port for word detail extraction."""

    async def extract_details(self, *, words: list[str]) -> dict[str, dict[str, Any]]: ...


@runtime_checkable
class PayloadValidatorPort(Protocol):
    """Port for payload validation."""

    def validate_payload(self, *, word: str, payload: dict[str, Any]) -> None: ...
