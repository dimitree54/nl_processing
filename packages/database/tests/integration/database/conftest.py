"""Shared fixtures for database integration tests against real Neon PostgreSQL."""

from collections.abc import AsyncIterator
import os

import pytest_asyncio

from nl_processing.database.backend.neon import NeonBackend

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["flashcard"]


@pytest_asyncio.fixture
async def neon_backend() -> AsyncIterator[NeonBackend]:
    """Function-scoped fixture: ensure tables exist, provide warmed-up backend.

    Uses idempotent ``CREATE TABLE IF NOT EXISTS`` — safe under pytest-xdist
    parallelism. No drop/reset; each test uses UUID-based data isolation.

    Holds a PostgreSQL **shared** advisory lock (key ``12345``) for the full
    test duration. The lifecycle test in ``test_table_creation.py`` acquires
    an **exclusive** lock on the same key before dropping ``user_words``,
    so it waits until all CRUD tests release their shared locks.
    """
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001

    # Shared lock: multiple CRUD tests can hold it concurrently.
    # Blocks only when the lifecycle test holds an exclusive lock.
    await conn.execute("SELECT pg_advisory_lock_shared(12345)")
    await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    await conn.fetchrow("SELECT 1")
    try:
        yield backend
    finally:
        await conn.execute("SELECT pg_advisory_unlock_shared(12345)")
