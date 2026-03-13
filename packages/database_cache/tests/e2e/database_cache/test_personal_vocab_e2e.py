"""E2E tests for personal vocab, progress summary, and delete APIs."""

from pathlib import Path
from uuid import uuid4

from nl_processing.database.models import PersonalWord
import pytest

from tests.e2e.database_cache.conftest import (
    WORDS,
    make_cache_service,
    seed_words,
)


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_list_personal_words_returns_complete_records(tmp_path: Path) -> None:
    """list_personal_words() returns PersonalWord objects with added_at and scores."""
    user_id = f"e2e_cache_{uuid4()}"
    await seed_words(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()

    assert len(personal_words) == len(WORDS)
    for pw in personal_words:
        assert isinstance(pw, PersonalWord)
        assert pw.added_at is not None
        assert isinstance(pw.scores, dict)
        assert "flashcard" in pw.scores
        assert pw.source_word_id > 0
        assert pw.target_word_id > 0
    source_forms = {pw.pair.source.normalized_form for pw in personal_words}
    expected_forms = {w.normalized_form for w in WORDS}
    assert source_forms == expected_forms


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_progress_summary_matches_reality(tmp_path: Path) -> None:
    """get_progress_summary() reports correct totals and negative counts."""
    user_id = f"e2e_cache_{uuid4()}"
    await seed_words(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    # All scores start at 0
    summary = await cache.get_progress_summary()
    assert "flashcard" in summary
    assert summary["flashcard"].total_words == len(WORDS)
    assert summary["flashcard"].negative_words == 0

    # Record -1 for one word
    await cache.record_exercise_result(source_word=WORDS[0], exercise_type="flashcard", delta=-1)
    summary_after = await cache.get_progress_summary()
    assert summary_after["flashcard"].negative_words == 1
    assert summary_after["flashcard"].total_words == len(WORDS)


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_delete_word_removes_from_cache_and_remote(tmp_path: Path) -> None:
    """delete_word() removes the word from remote and local cache."""
    user_id = f"e2e_cache_{uuid4()}"
    await seed_words(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()
    target_word = personal_words[0]
    target_id = target_word.source_word_id

    await cache.delete_word(target_id)

    # Verify locally: word is gone
    remaining = await cache.list_personal_words()
    assert len(remaining) == len(WORDS) - 1
    remaining_ids = {pw.source_word_id for pw in remaining}
    assert target_id not in remaining_ids

    # Verify progress summary updated
    summary = await cache.get_progress_summary()
    assert summary["flashcard"].total_words == len(WORDS) - 1

    # Verify after refresh: word doesn't reappear (deleted remotely)
    await cache.refresh()
    after_refresh = await cache.list_personal_words()
    assert len(after_refresh) == len(WORDS) - 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("db_ready")
async def test_delete_word_clears_pending_events(tmp_path: Path) -> None:
    """delete_word() also removes pending score events for the word (BR-6)."""
    user_id = f"e2e_cache_{uuid4()}"
    await seed_words(user_id)
    cache = make_cache_service(user_id, tmp_path)
    await cache.init()

    personal_words = await cache.list_personal_words()
    target_word = personal_words[0]

    # Record a score (creates pending event)
    await cache.record_exercise_result(source_word=target_word.pair.source, exercise_type="flashcard", delta=1)

    # Delete the word
    await cache.delete_word(target_word.source_word_id)

    # Verify pending events are cleaned up
    status = await cache.get_status()
    # Pending count should be 0 (the only pending event was for the deleted word)
    assert status.pending_events == 0
