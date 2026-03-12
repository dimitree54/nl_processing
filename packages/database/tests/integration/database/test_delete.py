"""Integration tests for delete operations with real Neon DB."""

import uuid

import pytest

from nl_processing.database.backend.neon import NeonBackend


@pytest.mark.asyncio
async def test_delete_operations_integration(neon_backend: NeonBackend) -> None:
    """Test delete operations against real Neon database."""
    # Use unique test data to avoid collisions
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    language = "nl"
    word_form = f"testword_{uuid.uuid4().hex[:8]}"
    word_type = "noun"

    # Add a word to the corpus
    word_id = await neon_backend.add_word("nl", word_form, word_type)
    assert word_id is not None

    # Associate word with user
    await neon_backend.add_user_word(user_id, word_id, language)

    # Add exercise score
    table = "nl_ru_flashcard"
    await neon_backend.increment_user_exercise_score(table, user_id, word_id, 5)

    # Verify word exists in user's vocabulary
    exists = await neon_backend.check_user_word_exists(user_id, word_id, language)
    assert exists is True

    # Verify exercise score exists
    scores = await neon_backend.get_user_exercise_scores(table, user_id, [word_id])
    assert len(scores) == 1
    assert scores[0]["score"] == 5

    # Delete exercise score
    await neon_backend.delete_user_exercise_score(table, user_id, word_id)

    # Verify exercise score is gone
    scores = await neon_backend.get_user_exercise_scores(table, user_id, [word_id])
    assert len(scores) == 0

    # Delete user word association
    await neon_backend.delete_user_word(user_id, word_id, language)

    # Verify user no longer has the word
    exists = await neon_backend.check_user_word_exists(user_id, word_id, language)
    assert exists is False

    # Verify word still exists in corpus
    word_dict = await neon_backend.get_word("nl", word_form)
    assert word_dict is not None
    assert word_dict["normalized_form"] == word_form
    assert word_dict["word_type"] == word_type


@pytest.mark.asyncio
async def test_check_user_word_exists_nonexistent(neon_backend: NeonBackend) -> None:
    """Test check_user_word_exists returns False for non-existent associations."""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    language = "nl"
    nonexistent_word_id = 999999

    exists = await neon_backend.check_user_word_exists(user_id, nonexistent_word_id, language)
    assert exists is False


@pytest.mark.asyncio
async def test_delete_user_word_nonexistent_noop(neon_backend: NeonBackend) -> None:
    """Test that deleting non-existent user-word association is a no-op."""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    language = "nl"
    nonexistent_word_id = 999999

    # This should not raise an error
    await neon_backend.delete_user_word(user_id, nonexistent_word_id, language)


@pytest.mark.asyncio
async def test_delete_user_exercise_score_nonexistent_noop(neon_backend: NeonBackend) -> None:
    """Test that deleting non-existent exercise score is a no-op."""
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    table = "nl_ru_flashcard"
    nonexistent_word_id = 999999

    # This should not raise an error
    await neon_backend.delete_user_exercise_score(table, user_id, nonexistent_word_id)
