"""Shared fixtures for database_cache unit tests."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.database.detailed_models import DetailedWordRecord, JsonValue
from nl_processing.database.models import EnrichedWordPairSnapshot
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
) -> EnrichedWordPairSnapshot:
    """Create an enriched snapshot payload with NL->RU defaults and added_at."""
    return EnrichedWordPairSnapshot(
        pair=WordPair(
            source=make_word(source_form, lang=Language.NL),
            target=make_word(target_form, lang=Language.RU),
        ),
        scores=scores or {},
        source_word_id=source_word_id,
        target_word_id=source_word_id + 1000,
        added_at=datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
    )


def make_remote_record(source_word: str, payload: dict[str, JsonValue]) -> DetailedWordRecord:
    """Create a DetailedWordRecord with noun defaults for unit tests."""
    return DetailedWordRecord(
        source_word=source_word,
        word_type="noun",
        schema_key="nl_ru_noun",
        schema_version=1,
        payload=payload,
    )


class MockProgressStore:
    """Fake remote progress sync port for testing."""

    def __init__(self, snapshot: list[EnrichedWordPairSnapshot] | None = None) -> None:
        self.snapshot: list[EnrichedWordPairSnapshot] = snapshot or []
        self.applied_deltas: list[dict[str, str | int]] = []
        self.apply_error: Exception | None = None

    async def export_remote_snapshot(self) -> list[EnrichedWordPairSnapshot]:
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


class MockRemoteDelete:
    """Fake remote delete port for testing."""

    def __init__(self) -> None:
        self.deleted_words: list[int] = []
        self.delete_error: Exception | None = None

    async def delete_word(self, source_word_id: int, exercise_types: list[str] | None = None) -> None:  # noqa: ARG002
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_words.append(source_word_id)

    async def delete_words(self, source_word_ids: list[int], exercise_types: list[str] | None = None) -> None:  # noqa: ARG002
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_words.extend(source_word_ids)


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
        remote_db=MockRemoteDelete(),
        local_store=local_store,
    )
    await svc.init()
    yield svc  # type: ignore[misc]
    await asyncio.sleep(0)
    await local_store.close()
