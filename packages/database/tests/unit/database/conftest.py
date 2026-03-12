"""Shared fixtures for database unit tests — MockBackend and service factories."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.service import DatabaseService
from tests.unit.database.mock_backend import MockBackend


class MockTranslator:
    """Fake translator that uppercases the normalized_form as 'translation'."""

    def __init__(self, target_language: Language) -> None:
        self._target = target_language

    async def translate(self, words: list[Word]) -> list[Word]:
        return [
            Word(normalized_form=w.normalized_form.upper(), word_type=w.word_type, language=self._target) for w in words
        ]


@pytest.fixture
def mock_backend() -> MockBackend:
    return MockBackend()


@pytest.fixture
def db_service(mock_backend: MockBackend) -> DatabaseService:
    return DatabaseService(
        user_id="u1",
        backend=mock_backend,
        translator=MockTranslator(target_language=Language.RU),
    )


@pytest.fixture
def delete_service(mock_backend: MockBackend) -> DatabaseService:
    """Service for delete tests without translator."""
    return DatabaseService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        backend=mock_backend,
    )


@pytest.fixture
def progress_store(mock_backend: MockBackend) -> ExerciseProgressStore:
    return ExerciseProgressStore(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=mock_backend,
    )


async def setup_word_with_translation(service: DatabaseService, mock_backend: MockBackend) -> int:
    """Helper to set up a word with translation and return its source_word_id."""
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
    return source_word_id
