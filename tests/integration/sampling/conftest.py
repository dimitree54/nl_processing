"""Shared fixtures for sampling integration tests against real Neon PostgreSQL."""

from collections.abc import AsyncIterator
import os
from uuid import uuid4

import pytest_asyncio

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.testing import drop_all_tables, reset_database

_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["nl_to_ru"]

_WORDS_DATA = [
    ("huis", "noun", "дом"),
    ("boek", "noun", "книга"),
    ("school", "noun", "школа"),
    ("water", "noun", "вода"),
    ("fiets", "noun", "велосипед"),
    ("lopen", "verb", "бежать"),
    ("lezen", "verb", "читать"),
    ("schrijven", "verb", "писать"),
    ("groot", "adjective", "большой"),
    ("klein", "adjective", "маленький"),
]

_POSITIVE_SCORED = ["huis", "boek", "school", "water", "fiets"]
_ZERO_SCORED = ["lopen", "lezen", "schrijven", "groot", "klein"]


async def _insert_words_and_scores(
    backend: NeonBackend,
    user_id: str,
) -> dict[str, int]:
    """Insert all test words, translations, user associations, and scores."""
    word_ids_nl: dict[str, int] = {}
    for nl_form, wtype, ru_form in _WORDS_DATA:
        nl_id = await backend.add_word("nl", nl_form, wtype)
        ru_id = await backend.add_word("ru", ru_form, wtype)
        assert nl_id is not None
        assert ru_id is not None
        await backend.add_translation_link("nl_ru", nl_id, ru_id)
        await backend.add_user_word(user_id, nl_id, "nl")
        word_ids_nl[nl_form] = nl_id
    for nl_form in _POSITIVE_SCORED:
        for _i in range(3):
            await backend.increment_user_exercise_score(
                "nl_ru_nl_to_ru",
                user_id,
                word_ids_nl[nl_form],
                1,
            )
    return word_ids_nl


@pytest_asyncio.fixture
async def populated_db() -> AsyncIterator[dict[str, str | int | list[str] | dict[str, int]]]:
    """Reset DB, insert test data, yield context, restore tables."""
    backend = NeonBackend(os.environ["DATABASE_URL"])
    conn = await backend._connect()  # noqa: SLF001
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        await reset_database(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
        user_id = f"sampling_test_{uuid4()}"
        word_ids_nl = await _insert_words_and_scores(backend, user_id)
        yield {
            "user_id": user_id,
            "word_ids_nl": word_ids_nl,
            "total_words": len(_WORDS_DATA),
            "positive_scored_words": _POSITIVE_SCORED,
            "zero_scored_words": _ZERO_SCORED,
        }
        await drop_all_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
        await backend.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")
