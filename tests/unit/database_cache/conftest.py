"""Shared fixtures for database_cache unit tests."""

from datetime import timedelta
from pathlib import Path

import pytest
import pytest_asyncio

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.models import ScoredWordPair, WordPair
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.service import DatabaseCacheService
from nl_processing.database_cache.sync import CacheSyncer


def make_word(form: str, pos: PartOfSpeech = PartOfSpeech.NOUN, lang: Language = Language.NL) -> Word:
    """Create a Word with minimal boilerplate."""
    return Word(normalized_form=form, word_type=pos, language=lang)


def make_scored_pair(
    source_form: str,
    target_form: str,
    source_word_id: int,
    scores: dict[str, int] | None = None,
) -> ScoredWordPair:
    """Create a ScoredWordPair with NL->RU defaults."""
    return ScoredWordPair(
        pair=WordPair(
            source=make_word(source_form, lang=Language.NL),
            target=make_word(target_form, lang=Language.RU),
        ),
        scores=scores or {},
        source_word_id=source_word_id,
    )


class MockProgressStore:
    """Fake ExerciseProgressStore for testing."""

    def __init__(self, snapshot: list[ScoredWordPair] | None = None) -> None:
        self.snapshot: list[ScoredWordPair] = snapshot or []
        self.applied_deltas: list[dict[str, str | int]] = []
        self.apply_error: Exception | None = None

    async def export_remote_snapshot(self) -> list[ScoredWordPair]:
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
async def cache_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DatabaseCacheService:
    """Fully-initialized DatabaseCacheService with mock remote."""
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
    )
    svc._local = LocalStore(str(tmp_path / "test.db"))
    await svc._local.open()
    mock_remote = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
            make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),
        ]
    )
    svc._syncer = CacheSyncer(svc._local, mock_remote)
    await svc._local.ensure_metadata(["flashcard"])
    await svc._syncer.refresh()
    svc._initialized = True
    yield svc  # type: ignore[misc]
    await svc._local.close()
