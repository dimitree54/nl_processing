"""Shared fixtures for database integration tests against real Neon PostgreSQL."""

from collections.abc import AsyncIterator
import os

from nl_processing.database_core.backend.neon import NeonBackend
import pytest_asyncio

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
