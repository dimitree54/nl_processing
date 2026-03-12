"""Unit tests for delete functionality."""

from datetime import timedelta
from pathlib import Path
import tempfile

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.exceptions import WordNotFoundError
import pytest

from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.service import DatabaseCacheService
from tests.unit.database_cache.conftest import MockRemoteDelete


@pytest.fixture
def delete_service(cache_service: DatabaseCacheService) -> DatabaseCacheService:
    """Service with MockRemoteDelete accessible for test manipulation."""
    return cache_service


@pytest.mark.asyncio
async def test_delete_word_removes_from_local_cache(delete_service: DatabaseCacheService) -> None:
    """Delete one word, verify it's removed from local cache but other words remain."""
    # Initially should have 2 words
    words = await delete_service.get_words()
    assert len(words) == 2
    source_word_ids = [w.source_word_id for w in await delete_service.get_word_pairs_with_scores()]
    assert 1 in source_word_ids
    assert 2 in source_word_ids

    # Delete word 1
    await delete_service.delete_word(1)

    # Should have 1 word remaining
    words = await delete_service.get_words()
    assert len(words) == 1
    remaining_ids = [w.source_word_id for w in await delete_service.get_word_pairs_with_scores()]
    assert 1 not in remaining_ids
    assert 2 in remaining_ids


@pytest.mark.asyncio
async def test_delete_word_removes_scores(delete_service: DatabaseCacheService) -> None:
    """Record a score, then delete the word - score should be gone."""
    # Record a score for word 1
    source_word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await delete_service.record_exercise_result(source_word=source_word, exercise_type="flashcard", delta=1)

    # Verify the score exists
    scored_pairs = await delete_service.get_word_pairs_with_scores()
    word1_pair = next(p for p in scored_pairs if p.source_word_id == 1)
    assert word1_pair.scores["flashcard"] == 1

    # Delete the word
    await delete_service.delete_word(1)

    # Word and its scores should be gone
    scored_pairs = await delete_service.get_word_pairs_with_scores()
    word1_pairs = [p for p in scored_pairs if p.source_word_id == 1]
    assert len(word1_pairs) == 0


@pytest.mark.asyncio
async def test_delete_word_removes_pending_events(delete_service: DatabaseCacheService) -> None:
    """Record an exercise result (creates pending event), delete word, verify events gone."""
    # Record exercise result to create pending event
    source_word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)

    await delete_service.record_exercise_result(source_word=source_word, exercise_type="flashcard", delta=1)

    # Verify pending event exists (use local store directly)
    assert delete_service._local is not None
    events = await delete_service._local._fetch_all("SELECT * FROM pending_score_events WHERE source_word_id = 1")
    assert len(events) > 0

    # Delete the word
    await delete_service.delete_word(1)

    # Pending events for that word should be gone
    events_after = await delete_service._local._fetch_all("SELECT * FROM pending_score_events WHERE source_word_id = 1")
    assert len(events_after) == 0


@pytest.mark.asyncio
async def test_delete_word_remote_failure_leaves_local_untouched(delete_service: DatabaseCacheService) -> None:
    """Mock remote raises ConnectionError, verify local cache still has the word."""
    # Get the mock remote delete and configure it to fail
    mock_remote = delete_service._remote_db  # type: ignore[attr-defined]
    assert isinstance(mock_remote, MockRemoteDelete)
    mock_remote.delete_error = ConnectionError("Network failure")

    # Verify word 1 exists before delete attempt
    words_before = await delete_service.get_words()
    assert len(words_before) == 2

    # Attempt delete should raise the error
    with pytest.raises(ConnectionError, match="Network failure"):
        await delete_service.delete_word(1)

    # Local cache should still have the word
    words_after = await delete_service.get_words()
    assert len(words_after) == 2
    source_word_ids = [w.source_word_id for w in await delete_service.get_word_pairs_with_scores()]
    assert 1 in source_word_ids
    assert 2 in source_word_ids


@pytest.mark.asyncio
async def test_delete_word_not_found_raises(delete_service: DatabaseCacheService) -> None:
    """Mock remote raises WordNotFoundError, verify it propagates."""
    # Get the mock remote delete and configure it to raise WordNotFoundError
    mock_remote = delete_service._remote_db  # type: ignore[attr-defined]
    assert isinstance(mock_remote, MockRemoteDelete)
    mock_remote.delete_error = WordNotFoundError("Word not found")

    # Delete should raise WordNotFoundError
    with pytest.raises(WordNotFoundError, match="Word not found"):
        await delete_service.delete_word(999)


@pytest.mark.asyncio
async def test_delete_words_batch(delete_service: DatabaseCacheService) -> None:
    """Delete 2 words at once, verify both removed."""
    # Initially should have 2 words
    words = await delete_service.get_words()
    assert len(words) == 2

    # Delete both words
    await delete_service.delete_words([1, 2])

    # Should have no words
    words = await delete_service.get_words()
    assert len(words) == 0


@pytest.mark.asyncio
async def test_delete_word_before_init_raises() -> None:
    """Verify CacheNotReadyError when calling delete before init."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        local_store = LocalStore(str(Path(tmp_dir) / "test.db"))
        svc = DatabaseCacheService(
            user_id="test_user",
            source_language=Language.NL,
            target_language=Language.RU,
            exercise_types=["flashcard"],
            cache_ttl=timedelta(minutes=30),
            cache_dir=tmp_dir,
            local_store=local_store,
        )
        # Don't call init()

        with pytest.raises(CacheNotReadyError, match="Cache not initialized"):
            await svc.delete_word(1)


@pytest.mark.asyncio
async def test_delete_empty_list_is_noop(delete_service: DatabaseCacheService) -> None:
    """Delete empty list should be a no-op."""
    words_before = await delete_service.get_words()

    await delete_service.delete_words([])

    words_after = await delete_service.get_words()
    assert len(words_after) == len(words_before)


@pytest.mark.asyncio
async def test_delete_word_calls_remote_with_exercise_types(delete_service: DatabaseCacheService) -> None:
    """Verify delete_word calls remote delete and passes word ID."""
    mock_remote = delete_service._remote_db  # type: ignore[attr-defined]
    assert isinstance(mock_remote, MockRemoteDelete)

    # Verify no words deleted initially
    assert len(mock_remote.deleted_words) == 0

    await delete_service.delete_word(1)

    # Verify the word was deleted remotely
    assert mock_remote.deleted_words == [1]
