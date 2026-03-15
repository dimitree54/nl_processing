"""Shared fixtures for database integration tests against real Neon PostgreSQL."""

from collections.abc import AsyncIterator
import os

from nl_processing.core.models import Word
import pytest_asyncio

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.detailed_models import DetailedWordRecord


class FakeExtractor:
    """Mock extractor for integration testing."""

    def __init__(self, results: list[DetailedWordRecord] | None = None) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results or []

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["flashcard"]


async def _close_backend_connection(backend: NeonBackend) -> None:
    """Close an open backend connection."""
    conn = backend._connection  # noqa: SLF001
    if conn is not None and not conn.is_closed():
        await conn.close()


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def integration_schema_ready() -> None:
    """Create the shared integration schema once per module."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    try:
        await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await _close_backend_connection(backend)


@pytest_asyncio.fixture
async def neon_backend(integration_schema_ready: None) -> AsyncIterator[NeonBackend]:  # noqa: ARG001
    """Function-scoped fixture: give each test its own backend connection."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    try:
        yield backend
    finally:
        await _close_backend_connection(backend)
