"""Shared fixtures for database_cache E2E tests against real Neon + file-based SQLite."""

from datetime import timedelta
from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_cache.service import DatabaseCacheService
from tests.e2e.database.conftest import db_ready as db_ready  # noqa: F401

WORDS = [
    Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    Word(normalized_form="lamp", word_type=PartOfSpeech.NOUN, language=Language.NL),
]

EXERCISE_TYPES = ["flashcard"]


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
