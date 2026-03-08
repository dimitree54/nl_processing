"""Shared fixtures for database_cache unit tests."""

import asyncio
from datetime import timedelta
from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair, WordPairSnapshot
import pytest_asyncio

from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.service import DatabaseCacheService


def make_word(form: str, pos: PartOfSpeech = PartOfSpeech.NOUN, lang: Language = Language.NL) -> Word:
    """Create a Word with minimal boilerplate."""
    return Word(normalized_form=form, word_type=pos, language=lang)


def make_scored_pair(
    source_form: str,
    target_form: str,
    source_word_id: int,
    scores: dict[str, int] | None = None,
) -> WordPairSnapshot:
    """Create a snapshot payload with NL->RU defaults."""
    return WordPairSnapshot(
        pair=WordPair(
            source=make_word(source_form, lang=Language.NL),
            target=make_word(target_form, lang=Language.RU),
        ),
        scores=scores or {},
        source_word_id=source_word_id,
        target_word_id=source_word_id + 1000,
    )


class MockProgressStore:
    """Fake remote progress sync port for testing."""

    def __init__(self, snapshot: list[WordPairSnapshot] | None = None) -> None:
        self.snapshot: list[WordPairSnapshot] = snapshot or []
        self.applied_deltas: list[dict[str, str | int]] = []
        self.apply_error: Exception | None = None

    async def export_remote_snapshot(self) -> list[WordPairSnapshot]:
        return list(self.snapshot)

    async def apply_score_delta(
        self,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        if self.apply_error is not None:
            raise self.apply_error
        self.applied_deltas.append({
            "event_id": event_id,
            "source_word_id": source_word_id,
            "exercise_type": exercise_type,
            "delta": delta,
        })


@pytest_asyncio.fixture
async def local_store() -> LocalStore:
    """In-memory LocalStore opened and ready for use."""
    store = LocalStore(":memory:")
    await store.open()
    yield store  # type: ignore[misc]
    await store.close()


@pytest_asyncio.fixture
async def cache_service(tmp_path: Path) -> DatabaseCacheService:
    """Fully-initialized DatabaseCacheService with mock remote."""
    local_store = LocalStore(str(tmp_path / "test.db"))
    svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
        remote_progress=MockProgressStore(
            snapshot=[
                make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
                make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),
            ]
        ),
        local_store=local_store,
    )
    await svc.init()
    yield svc  # type: ignore[misc]
    await asyncio.sleep(0)
    await local_store.close()
