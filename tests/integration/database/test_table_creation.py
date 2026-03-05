"""Integration tests for table creation against real Neon PostgreSQL.

These tests verify ``create_tables`` (IF NOT EXISTS) and ``reset_database``
using **isolated language codes** (``de``, ``fr``) so that they never touch
the ``nl``/``ru`` tables used by parallel CRUD workers.

``drop_all_tables`` drops the shared ``user_words`` table, so the lifecycle
test uses a PostgreSQL advisory lock to serialize with CRUD workers.
"""

import os
import uuid

import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import (
    count_words,
    drop_all_tables,
    reset_database,
)

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]

_EXPECTED_TABLES = [
    "words_nl",
    "words_ru",
    "translations_nl_ru",
    "user_words",
    "user_word_exercise_scores_nl_ru",
]

# Isolated language codes for destructive DDL tests — never collide with CRUD tests.
_ISO_LANGUAGES = ["de", "fr"]
_ISO_PAIRS = [("de", "fr")]
_ISO_EXPECTED = [
    "words_de",
    "words_fr",
    "translations_de_fr",
    "user_words",
    "user_word_exercise_scores_de_fr",
]


async def _table_exists(backend: NeonBackend, table_name: str) -> bool:
    """Check if a table exists in the database via information_schema."""
    conn = await backend._connect()  # noqa: SLF001
    row = await conn.fetchrow(
        "SELECT EXISTS (  SELECT 1 FROM information_schema.tables WHERE table_name = $1) AS exists",
        table_name,
    )
    return bool(row["exists"])  # type: ignore[index]


@pytest.mark.asyncio
async def test_create_tables_creates_all_expected_tables() -> None:
    """create_tables creates all expected tables (IF NOT EXISTS)."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    await backend.create_tables(_LANGUAGES, _PAIRS)

    for table_name in _EXPECTED_TABLES:
        exists = await _table_exists(backend, table_name)
        assert exists, f"Table '{table_name}' should exist after create_tables"


@pytest.mark.asyncio
async def test_create_tables_is_idempotent() -> None:
    """Calling create_tables twice does not raise an error."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    await backend.create_tables(_LANGUAGES, _PAIRS)
    await backend.create_tables(_LANGUAGES, _PAIRS)

    for table_name in _EXPECTED_TABLES:
        exists = await _table_exists(backend, table_name)
        assert exists, f"Table '{table_name}' should still exist after idempotent create"


@pytest.mark.asyncio
async def test_drop_and_reset_full_lifecycle() -> None:
    """Table lifecycle: create → drop → verify gone → reset → verify clean.

    Uses isolated language codes (de/fr) so language-specific tables never
    collide with parallel CRUD tests on nl/ru. A PostgreSQL advisory lock
    (key ``12345``) serializes the ``user_words`` drop/recreate window with
    the CRUD conftest fixture, which acquires the same lock before using
    ``user_words``.
    """
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001

    # Advisory lock prevents CRUD workers from reading user_words mid-drop.
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        # 1. Ensure isolated tables exist
        await backend.create_tables(_ISO_LANGUAGES, _ISO_PAIRS)
        for name in _ISO_EXPECTED:
            assert await _table_exists(backend, name), f"Setup: '{name}' should exist"

        # 2. Drop all isolated tables and verify they are gone
        await drop_all_tables(_ISO_LANGUAGES, _ISO_PAIRS)
        for name in _ISO_EXPECTED:
            exists = await _table_exists(backend, name)
            assert not exists, f"'{name}' should NOT exist after drop_all_tables"

        # 3. Reset database: creates clean empty tables
        await reset_database(_ISO_LANGUAGES, _ISO_PAIRS)
        for name in _ISO_EXPECTED:
            exists = await _table_exists(backend, name)
            assert exists, f"'{name}' should exist after reset_database"

        # 4. Insert data, then verify reset clears it
        word = f"lifecycle_{uuid.uuid4().hex[:8]}"
        await backend.add_word("de", word, "noun")
        assert await count_words("de") >= 1

        await reset_database(_ISO_LANGUAGES, _ISO_PAIRS)
        assert await count_words("de") == 0, "words_de should be empty after reset"

        # 5. Clean up isolated tables and restore shared ones (still under lock).
        # drop_all_tables also drops user_words; create_tables restores it.
        await drop_all_tables(_ISO_LANGUAGES, _ISO_PAIRS)
        await backend.create_tables(_LANGUAGES, _PAIRS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")
