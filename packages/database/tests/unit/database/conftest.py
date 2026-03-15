"""Shared fixtures for database unit tests — MockBackend and service factories."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.service import DatabaseService
from tests.unit.database.mock_backend import MockBackend


class FakeValidator:
    """Mock payload validator for testing."""

    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, int, dict]] = []
        self._error = error

    def validate_payload(self, schema_key: str, schema_version: int, payload: dict) -> None:
        self.calls.append((schema_key, schema_version, payload))
        if self._error is not None:
            raise self._error


class FakeExtractor:
    """Mock extractor for testing."""

    def __init__(self, results: list[DetailedWordRecord] | None = None) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results or []

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


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


@pytest.fixture
def detailed_backend() -> MockBackend:
    """Create a mock backend for detailed store testing."""
    return MockBackend()


@pytest.fixture
def detailed_store(detailed_backend: MockBackend) -> DetailedWordStore:
    """Create a DetailedWordStore with mock backend."""
    return DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=detailed_backend,
    )


def make_detailed_record(
    source_word: str = "kat",
    word_type: str = "noun",
    schema_key: str = "nl_ru_noun",
    schema_version: int = 1,
    payload: dict | None = None,
) -> DetailedWordRecord:
    """Create a DetailedWordRecord with sensible defaults."""
    return DetailedWordRecord(
        source_word=source_word,
        word_type=word_type,
        schema_key=schema_key,
        schema_version=schema_version,
        payload=payload or {},
    )


async def add_word_with_detail(
    backend: MockBackend,
    normalized_form: str = "hond",
    word_type: str = "noun",
    schema_key: str = "nl_ru_noun",
    payload: dict | None = None,
) -> tuple[int, dict]:
    """Add a word to corpus and persist a detailed record. Returns (word_id, payload)."""
    word_id = await backend.add_word("nl", normalized_form, word_type)
    assert word_id is not None
    actual_payload = payload or {"article": "de", "plural": "honden"}
    await backend.upsert_word_details(
        f"word_details_nl_ru", word_id, word_type, schema_key, 1, json.dumps(actual_payload)
    )
    return word_id, actual_payload


async def setup_extraction_test(
    backend: MockBackend,
    extractor: "FakeExtractor",
    normalized_form: str = "kat",
    payload: dict | None = None,
) -> tuple[int, dict, Word]:
    """Add word to corpus and configure extractor with a matching record."""
    actual_payload = payload or {"article": "de", "plural": "katten"}
    word_id = await backend.add_word("nl", normalized_form, "noun")
    assert word_id is not None
    record = make_detailed_record(source_word=normalized_form, payload=actual_payload)
    extractor._results = [record]
    word = Word(normalized_form=normalized_form, word_type=PartOfSpeech.NOUN, language=Language.NL)
    return word_id, actual_payload, word


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
