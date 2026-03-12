"""Unit tests for ExerciseProgressStore.get_progress_summary()."""

from nl_processing.core.models import Language
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.unit.database.conftest import MockBackend


async def _seed_word_pair(backend: MockBackend, source_word: str = "huis", target_word: str = "HUIS") -> int:
    """Insert word pair with user association and translation link, return source_id."""
    src_id = await backend.add_word("nl", source_word, "noun")
    tgt_id = await backend.add_word("ru", target_word, "noun")
    assert src_id is not None
    assert tgt_id is not None
    await backend.add_user_word("u1", src_id, "nl")
    await backend.add_translation_link("nl_ru", src_id, tgt_id)
    return src_id


@pytest.mark.asyncio
async def test_get_progress_summary_all_positive(
    progress_store: ExerciseProgressStore, mock_backend: MockBackend
) -> None:
    """3 words, all scores ≥ 0 → negative_words=0, negative_percentage=0.0."""
    await _seed_word_pair(mock_backend, "huis", "HUIS")
    await _seed_word_pair(mock_backend, "lopen", "LOPEN")
    await _seed_word_pair(mock_backend, "snel", "SNEL")

    # Set positive scores
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=1)
    await progress_store.increment(source_word_id=2, exercise_type="flashcard", delta=1)
    await progress_store.increment(source_word_id=3, exercise_type="flashcard", delta=1)

    summary = await progress_store.get_progress_summary()
    assert summary["flashcard"].total_words == 3
    assert summary["flashcard"].negative_words == 0
    assert summary["flashcard"].negative_ratio == 0.0
    assert summary["flashcard"].negative_percentage == 0.0


@pytest.mark.asyncio
async def test_get_progress_summary_some_negative(
    progress_store: ExerciseProgressStore, mock_backend: MockBackend
) -> None:
    """3 words, 1 with negative score → negative_words=1, negative_ratio=1/3, negative_percentage≈33.33."""
    await _seed_word_pair(mock_backend, "huis", "HUIS")
    await _seed_word_pair(mock_backend, "lopen", "LOPEN")
    await _seed_word_pair(mock_backend, "snel", "SNEL")

    # Set one negative, others positive/zero
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=-1)
    await progress_store.increment(source_word_id=2, exercise_type="flashcard", delta=1)
    # word 3 has no score (defaults to 0)

    summary = await progress_store.get_progress_summary()
    assert summary["flashcard"].total_words == 3
    assert summary["flashcard"].negative_words == 1
    assert summary["flashcard"].negative_ratio == pytest.approx(1 / 3)
    assert summary["flashcard"].negative_percentage == pytest.approx(33.333333333333336)


@pytest.mark.asyncio
async def test_get_progress_summary_all_negative(
    progress_store: ExerciseProgressStore, mock_backend: MockBackend
) -> None:
    """All scores < 0 → negative_words=total_words, negative_percentage=100.0."""
    await _seed_word_pair(mock_backend, "huis", "HUIS")
    await _seed_word_pair(mock_backend, "lopen", "LOPEN")

    # Set all negative
    await progress_store.increment(source_word_id=1, exercise_type="flashcard", delta=-1)
    await progress_store.increment(source_word_id=2, exercise_type="flashcard", delta=-1)

    summary = await progress_store.get_progress_summary()
    assert summary["flashcard"].total_words == 2
    assert summary["flashcard"].negative_words == 2
    assert summary["flashcard"].negative_ratio == 1.0
    assert summary["flashcard"].negative_percentage == 100.0


@pytest.mark.asyncio
async def test_get_progress_summary_missing_scores_not_negative(
    progress_store: ExerciseProgressStore, mock_backend: MockBackend
) -> None:
    """No scores → all default to 0 → negative_words=0."""
    await _seed_word_pair(mock_backend, "huis", "HUIS")
    await _seed_word_pair(mock_backend, "lopen", "LOPEN")

    # No scores set - should default to 0
    summary = await progress_store.get_progress_summary()
    assert summary["flashcard"].total_words == 2
    assert summary["flashcard"].negative_words == 0
    assert summary["flashcard"].negative_ratio == 0.0
    assert summary["flashcard"].negative_percentage == 0.0


@pytest.mark.asyncio
async def test_get_progress_summary_empty_vocabulary(progress_store: ExerciseProgressStore) -> None:
    """No words → total_words=0, negative_words=0, negative_percentage=0.0."""
    summary = await progress_store.get_progress_summary()
    assert summary["flashcard"].total_words == 0
    assert summary["flashcard"].negative_words == 0
    assert summary["flashcard"].negative_ratio == 0.0
    assert summary["flashcard"].negative_percentage == 0.0


@pytest.mark.asyncio
async def test_get_progress_summary_multiple_exercise_types(mock_backend: MockBackend) -> None:
    """Two exercise types → dict has both keys with independent calculations."""
    # Create store with two exercise types
    store = ExerciseProgressStore(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard", "typing"],
        backend=mock_backend,
    )

    await _seed_word_pair(mock_backend, "huis", "HUIS")
    await _seed_word_pair(mock_backend, "lopen", "LOPEN")

    # Set different scores for different exercise types
    await store.increment(source_word_id=1, exercise_type="flashcard", delta=-1)  # negative flashcard
    await store.increment(source_word_id=1, exercise_type="typing", delta=1)  # positive typing
    await store.increment(source_word_id=2, exercise_type="flashcard", delta=1)  # positive flashcard
    await store.increment(source_word_id=2, exercise_type="typing", delta=-1)  # negative typing

    summary = await store.get_progress_summary()

    # Both should have 2 total words
    assert summary["flashcard"].total_words == 2
    assert summary["typing"].total_words == 2

    # Each should have 1 negative word
    assert summary["flashcard"].negative_words == 1  # word 1 negative
    assert summary["typing"].negative_words == 1  # word 2 negative

    # Both should have 50% negative
    assert summary["flashcard"].negative_ratio == 0.5
    assert summary["flashcard"].negative_percentage == 50.0
    assert summary["typing"].negative_ratio == 0.5
    assert summary["typing"].negative_percentage == 50.0
