"""Unit tests for delete_word() and delete_words() APIs."""

import pytest

from nl_processing.database.exceptions import WordNotFoundError
from nl_processing.database.service import DatabaseService
from tests.unit.database.conftest import setup_word_with_translation
from tests.unit.database.mock_backend import MockBackend


@pytest.mark.asyncio
async def test_delete_word_removes_membership(delete_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word removes the user-word association."""
    source_word_id = await setup_word_with_translation(delete_service, mock_backend)

    # Verify it exists
    user_words = await delete_service.get_words()
    assert len(user_words) == 1

    # Delete the word
    await delete_service.delete_word(source_word_id)

    # Verify it's gone
    user_words = await delete_service.get_words()
    assert len(user_words) == 0


@pytest.mark.asyncio
async def test_delete_word_removes_exercise_scores(delete_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word removes exercise scores when exercise_types specified."""
    source_word_id = await setup_word_with_translation(delete_service, mock_backend)

    # Add some exercise scores
    await mock_backend.increment_user_exercise_score("nl_ru_flashcard", "test_user", source_word_id, 5)
    scores = await mock_backend.get_user_exercise_scores("nl_ru_flashcard", "test_user", [source_word_id])
    assert len(scores) == 1
    assert scores[0]["score"] == 5

    # Delete with exercise types
    await delete_service.delete_word(source_word_id, exercise_types=["flashcard"])

    # Verify scores are gone
    scores = await mock_backend.get_user_exercise_scores("nl_ru_flashcard", "test_user", [source_word_id])
    assert len(scores) == 0


@pytest.mark.asyncio
async def test_delete_word_preserves_corpus(delete_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word preserves the word in the corpus."""
    source_word_id = await setup_word_with_translation(delete_service, mock_backend)

    # Delete the user association
    await delete_service.delete_word(source_word_id)

    # Verify word still exists in corpus
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    assert word_dict["normalized_form"] == "hond"


@pytest.mark.asyncio
async def test_delete_word_not_found_raises(delete_service: DatabaseService) -> None:
    """Test that deleting a non-existent word raises WordNotFoundError."""
    with pytest.raises(WordNotFoundError, match="Source word ID 999 not in user's vocabulary"):
        await delete_service.delete_word(999)
