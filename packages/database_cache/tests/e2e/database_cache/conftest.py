"""Shared fixtures for database_cache E2E tests against real Neon + file-based SQLite."""

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
import os
from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import (
    count_translation_links,
    drop_all_tables,
    reset_database,
)
from nl_processing.translate_word.service import WordTranslator
import pytest_asyncio

from nl_processing.database_cache.service import DatabaseCacheService

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["flashcard"]

WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

EXERCISE_TYPES = ["flashcard"]


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
    """Function-scoped fixture: reset DB before test, drop tables after."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        await reset_database(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
        yield
        await drop_all_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
        await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")


def make_database_service(user_id: str) -> DatabaseService:
    """Create a DatabaseService composed with the translate_word package."""
    return DatabaseService(
        user_id=user_id,
        translator=WordTranslator(source_language=Language.NL, target_language=Language.RU),
    )


def make_cache_service(user_id: str, tmp_path: Path) -> DatabaseCacheService:
    """Create a DatabaseCacheService backed by real Neon + file-based SQLite."""
    return DatabaseCacheService(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=EXERCISE_TYPES,
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
    )
