"""Shared fixtures for database unit tests — MockBackend and service factories."""

from nl_processing.core.models import Language, Word
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
def progress_store(mock_backend: MockBackend) -> ExerciseProgressStore:
    return ExerciseProgressStore(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=mock_backend,
    )
