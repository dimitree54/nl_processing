"""Shared fixtures for database_cache E2E tests against real Neon + file-based SQLite."""

from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest_asyncio

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.service import DatabaseService
from nl_processing.database_cache.service import DatabaseCacheService
from tests.e2e.database.conftest import (
    db_ready as db_ready,  # noqa: F401
    wait_for_translations,
)

WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

EXERCISE_TYPES = ["flashcard"]


@pytest_asyncio.fixture
async def seeded_user() -> str:
    """Add test words to Neon and wait for translations. Returns the user_id."""
    user_id = f"e2e_cache_{uuid4()}"
    service = DatabaseService(user_id=user_id)
    await service.add_words(WORDS)
    await wait_for_translations(len(WORDS))
    return user_id


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
