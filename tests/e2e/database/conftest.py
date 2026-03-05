"""Shared fixtures for database e2e tests against real Neon PostgreSQL + OpenAI."""

import asyncio
from collections.abc import AsyncIterator
import os

import pytest_asyncio

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import (
    count_translation_links,
    drop_all_tables,
    reset_database,
)

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]


async def wait_for_translations(expected_count: int, table: str = "nl_ru", timeout: float = 15.0) -> None:
    """Poll until translation_links reach expected count or timeout."""
    elapsed = 0.0
    while elapsed < timeout:
        count = await count_translation_links(table)
        if count >= expected_count:
            return
        await asyncio.sleep(1.0)
        elapsed += 1.0
    actual = await count_translation_links(table)
    msg = f"Translations did not complete within {timeout}s (expected={expected_count}, actual={actual})"
    raise AssertionError(msg)


@pytest_asyncio.fixture
async def db_ready() -> AsyncIterator[None]:
    """Function-scoped fixture: reset DB before test, drop tables after.

    Acquires an exclusive advisory lock (key 12345) to serialize with
    integration tests that use shared locks on the same key.
    """
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        await reset_database(_LANGUAGES, _PAIRS)
        yield
        await drop_all_tables(_LANGUAGES, _PAIRS)
        await backend.create_tables(_LANGUAGES, _PAIRS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")
