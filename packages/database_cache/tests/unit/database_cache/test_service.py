"""Unit tests for DatabaseCacheService — public API for the local cache layer."""

import asyncio
from datetime import timedelta
from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair
import pytest

from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.service import DatabaseCacheService
from tests.unit.database_cache.conftest import MockProgressStore, make_scored_pair


def test_constructor_validates_exercise_types(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty exercise_types list raises ValueError at construction time."""
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    with pytest.raises(ValueError, match="exercise_types must be a non-empty list"):
        DatabaseCacheService(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            exercise_types=[],
            cache_ttl=timedelta(minutes=30),
        )


@pytest.mark.asyncio
async def test_get_words_before_init_raises() -> None:
    """Calling get_words before init() raises CacheNotReadyError."""
    svc = DatabaseCacheService(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
    )
    with pytest.raises(CacheNotReadyError):
        await svc.get_words()


@pytest.mark.asyncio
async def test_get_word_pairs_before_init_raises() -> None:
    """Calling get_word_pairs_with_scores before init() raises CacheNotReadyError."""
    svc = DatabaseCacheService(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
    )
    with pytest.raises(CacheNotReadyError):
        await svc.get_word_pairs_with_scores()


@pytest.mark.asyncio
async def test_init_with_injected_remote_skips_database_url(tmp_path: Path) -> None:
    """Injected remote_progress avoids DATABASE_URL lookup during init()."""
    svc = DatabaseCacheService(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        remote_progress=MockProgressStore(
            snapshot=[make_scored_pair("huis", "dom", 1, {"flashcard": 0})],
        ),
        local_store=LocalStore(str(tmp_path / "cache.db")),
    )

    status = await svc.init()

    assert status.is_ready is True


@pytest.mark.asyncio
async def test_get_words_returns_word_pairs(cache_service: DatabaseCacheService) -> None:
    """get_words returns a list of WordPair objects."""
    result = await cache_service.get_words()
    assert len(result) == 2
    assert all(isinstance(wp, WordPair) for wp in result)
    forms = {wp.source.normalized_form for wp in result}
    assert forms == {"huis", "boek"}


@pytest.mark.asyncio
async def test_get_word_pairs_with_scores(cache_service: DatabaseCacheService) -> None:
    """get_word_pairs_with_scores returns ScoredWordPair objects with scores."""
    result = await cache_service.get_word_pairs_with_scores()
    assert len(result) == 2
    assert all(isinstance(sp, ScoredWordPair) for sp in result)
    for sp in result:
        assert "flashcard" in sp.scores


@pytest.mark.asyncio
async def test_record_exercise_result_validates_type(cache_service: DatabaseCacheService) -> None:
    """Unknown exercise_type raises ValueError."""
    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    with pytest.raises(ValueError, match="Unknown exercise_type"):
        await cache_service.record_exercise_result(source_word=word, exercise_type="typing", delta=1)


@pytest.mark.asyncio
async def test_record_exercise_result_validates_delta(cache_service: DatabaseCacheService) -> None:
    """delta=0 raises ValueError."""
    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    with pytest.raises(ValueError, match="delta must be"):
        await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=0)


@pytest.mark.asyncio
async def test_record_exercise_result_updates_locally(cache_service: DatabaseCacheService) -> None:
    """Recording a result changes the local score."""
    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)
    scored = await cache_service.get_word_pairs_with_scores()
    huis_scores = [sp for sp in scored if sp.pair.source.normalized_form == "huis"]
    assert len(huis_scores) == 1
    assert huis_scores[0].scores["flashcard"] == 1


@pytest.mark.asyncio
async def test_get_status_returns_cache_status(cache_service: DatabaseCacheService) -> None:
    """get_status returns a CacheStatus with correct fields."""
    status = await cache_service.get_status()
    assert isinstance(status, CacheStatus)
    assert status.is_ready is True
    assert status.has_snapshot is True
    assert status.pending_events == 0


@pytest.mark.asyncio
async def test_record_exercise_result_triggers_background_flush(
    cache_service: DatabaseCacheService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """record_exercise_result() spawns a background flush task."""
    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    calls: list[object] = []
    monkeypatch.setattr(asyncio, "create_task", lambda coro: calls.append(coro) or coro.close())  # type: ignore[func-returns-value]
    await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_auto_flush_delivers_events_to_remote(cache_service: DatabaseCacheService) -> None:
    """Auto-flush after record_exercise_result() pushes events to remote."""
    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await cache_service.record_exercise_result(source_word=word, exercise_type="flashcard", delta=1)
    await asyncio.sleep(0)  # yield to event loop so background task runs
    status = await cache_service.get_status()
    assert status.pending_events == 0
