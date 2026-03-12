"""Unit tests for personal vocabulary functionality."""

from datetime import datetime

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.models import PersonalWord
from nl_processing.database.service import DatabaseService
from tests.unit.database.conftest import MockBackend

_HUIS = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)
_DOM = Word(normalized_form="DOM", word_type=PartOfSpeech.NOUN, language=Language.RU)


@pytest.mark.asyncio
async def test_list_personal_words_returns_entries(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Seeded word pair returns PersonalWord with correct fields."""
    # Add source and target words
    await db_service.add_words([_HUIS])

    # Manually add translated target word and link for test
    await mock_backend.add_word("ru", _DOM.normalized_form, _DOM.word_type.value)
    await mock_backend.add_translation_link("nl_ru", 1, 1)  # source_id=1, target_id=1

    # Add some score data
    mock_backend._scores[("nl_ru_flashcard", "u1", 1)] = 5

    result = await db_service.list_personal_words(exercise_types=["flashcard"])

    assert len(result) == 1
    personal_word = result[0]
    assert isinstance(personal_word, PersonalWord)
    assert personal_word.pair.source.normalized_form == "huis"
    assert personal_word.pair.target.normalized_form == "DOM"
    assert personal_word.source_word_id == 1
    assert personal_word.target_word_id == 1
    assert personal_word.scores == {"flashcard": 5}


@pytest.mark.asyncio
async def test_list_personal_words_includes_added_at(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """added_at field is a datetime."""
    await db_service.add_words([_HUIS])
    await mock_backend.add_word("ru", _DOM.normalized_form, _DOM.word_type.value)
    await mock_backend.add_translation_link("nl_ru", 1, 1)

    result = await db_service.list_personal_words(exercise_types=["flashcard"])

    assert len(result) == 1
    assert isinstance(result[0].added_at, datetime)


@pytest.mark.asyncio
async def test_list_personal_words_includes_scores(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Seeded score data is populated in scores field."""
    await db_service.add_words([_HUIS])
    await mock_backend.add_word("ru", _DOM.normalized_form, _DOM.word_type.value)
    await mock_backend.add_translation_link("nl_ru", 1, 1)

    # Add score data
    mock_backend._scores[("nl_ru_flashcard", "u1", 1)] = 3

    result = await db_service.list_personal_words(exercise_types=["flashcard"])

    assert len(result) == 1
    assert result[0].scores == {"flashcard": 3}


@pytest.mark.asyncio
async def test_list_personal_words_missing_scores_default_zero(
    db_service: DatabaseService, mock_backend: MockBackend
) -> None:
    """Missing scores default to 0."""
    await db_service.add_words([_HUIS])
    await mock_backend.add_word("ru", _DOM.normalized_form, _DOM.word_type.value)
    await mock_backend.add_translation_link("nl_ru", 1, 1)

    # No score data added
    result = await db_service.list_personal_words(exercise_types=["flashcard"])

    assert len(result) == 1
    assert result[0].scores == {"flashcard": 0}


@pytest.mark.asyncio
async def test_list_personal_words_empty(db_service: DatabaseService) -> None:
    """No words returns empty list."""
    result = await db_service.list_personal_words(exercise_types=["flashcard"])
    assert result == []


@pytest.mark.asyncio
async def test_list_personal_words_no_exercise_types(db_service: DatabaseService, mock_backend: MockBackend) -> None:
    """Call with exercise_types=None returns empty scores dict."""
    await db_service.add_words([_HUIS])
    await mock_backend.add_word("ru", _DOM.normalized_form, _DOM.word_type.value)
    await mock_backend.add_translation_link("nl_ru", 1, 1)

    result = await db_service.list_personal_words(exercise_types=None)

    assert len(result) == 1
    assert result[0].scores == {}
