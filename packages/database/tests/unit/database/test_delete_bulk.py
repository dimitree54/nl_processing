"""Unit tests for bulk delete operations and edge cases."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

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
async def test_delete_words_bulk(service: DatabaseService, mock_backend: MockBackend) -> None:
    """Test that delete_words removes multiple words."""
    # Add multiple words
    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    await service.add_words(words)

    # Manually add translated target words and links for test
    await mock_backend.add_word("ru", "собака", "noun")
    await mock_backend.add_word("ru", "кошка", "noun")
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # hond -> собака
    await mock_backend.add_translation_link("nl_ru", 2, 2)  # kat -> кошка

    # Get word IDs
    hond_dict = await mock_backend.get_word("nl", "hond")
    kat_dict = await mock_backend.get_word("nl", "kat")
    assert hond_dict is not None
    assert kat_dict is not None
    source_word_ids = [int(hond_dict["id"]), int(kat_dict["id"])]

    # Verify they exist
    user_words = await service.get_words()
    assert len(user_words) == 2

    # Delete both
    await service.delete_words(source_word_ids)

    # Verify they're gone
    user_words = await service.get_words()
    assert len(user_words) == 0


@pytest.mark.asyncio
async def test_delete_words_empty_list_noop(service: DatabaseService) -> None:
    """Test that delete_words with empty list does nothing."""
    # This should not raise an error
    await service.delete_words([])


@pytest.mark.asyncio
async def test_delete_word_other_users_unaffected() -> None:
    """Test that delete_word for one user doesn't affect another user."""
    mock_backend = MockBackend()

    service1 = DatabaseService(
        user_id="user1",
        source_language=Language.NL,
        target_language=Language.RU,
        backend=mock_backend,
    )

    service2 = DatabaseService(
        user_id="user2",
        source_language=Language.NL,
        target_language=Language.RU,
        backend=mock_backend,
    )

    # Both users add the same word
    word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
    await service1.add_words([word])
    await service2.add_words([word])

    # Manually add translated target word and link for test
    await mock_backend.add_word("ru", "собака", "noun")
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # source_id=1, target_id=1

    # Get word ID
    word_dict = await mock_backend.get_word("nl", "hond")
    assert word_dict is not None
    source_word_id = int(word_dict["id"])

    # User1 deletes the word
    await service1.delete_word(source_word_id)

    # User1 should have no words
    user1_words = await service1.get_words()
    assert len(user1_words) == 0

    # User2 should still have the word
    user2_words = await service2.get_words()
    assert len(user2_words) == 1
    assert user2_words[0].source.normalized_form == "hond"
