"""Unit tests for delete_word() and delete_words() APIs."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.exceptions import WordNotFoundError
from nl_processing.database.service import DatabaseService
from tests.unit.database.mock_backend import MockBackend


@pytest.fixture
def mock_backend() -> MockBackend:
    return MockBackend()


@pytest.fixture
def service(mock_backend: MockBackend) -> DatabaseService:
    return DatabaseService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        backend=mock_backend,
    )


@pytest.mark.asyncio
async def test_delete_word_removes_membership(service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word removes the user-word association."""
    # Add a word
    word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await service.add_words([word])

    # Manually add translated target word and link for test
    await mock_backend.add_word("ru", "собака", "noun")
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # source_id=1, target_id=1

    # Verify it exists
    user_words = await service.get_words()
    assert len(user_words) == 1

    # Get the source word ID from mock backend
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    source_word_id = int(word_dict["id"])

    # Delete the word
    await service.delete_word(source_word_id)

    # Verify it's gone
    user_words = await service.get_words()
    assert len(user_words) == 0


@pytest.mark.asyncio
async def test_delete_word_removes_exercise_scores(service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word removes exercise scores when exercise_types specified."""
    # Add a word
    word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await service.add_words([word])

    # Manually add translated target word and link for test
    await mock_backend.add_word("ru", "собака", "noun")
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # source_id=1, target_id=1

    # Get the source word ID
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    source_word_id = int(word_dict["id"])

    # Add some exercise scores
    await mock_backend.increment_user_exercise_score("nl_ru_flashcard", "test_user", source_word_id, 5)
    scores = await mock_backend.get_user_exercise_scores("nl_ru_flashcard", "test_user", [source_word_id])
    assert len(scores) == 1
    assert scores[0]["score"] == 5

    # Delete with exercise types
    await service.delete_word(source_word_id, exercise_types=["flashcard"])

    # Verify scores are gone
    scores = await mock_backend.get_user_exercise_scores("nl_ru_flashcard", "test_user", [source_word_id])
    assert len(scores) == 0


@pytest.mark.asyncio
async def test_delete_word_preserves_corpus(service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_word preserves the word in the corpus."""
    # Add a word
    word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await service.add_words([word])

    # Manually add translated target word and link for test
    await mock_backend.add_word("ru", "собака", "noun")
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # source_id=1, target_id=1

    # Get the source word ID
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    source_word_id = int(word_dict["id"])

    # Delete the user association
    await service.delete_word(source_word_id)

    # Verify word still exists in corpus
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    assert word_dict["normalized_form"] == "hond"


@pytest.mark.asyncio
async def test_delete_word_not_found_raises(service: DatabaseService) -> None:
    """Test that deleting a non-existent word raises WordNotFoundError."""
    with pytest.raises(WordNotFoundError, match="Source word ID 999 not in user's vocabulary"):
        await service.delete_word(999)
