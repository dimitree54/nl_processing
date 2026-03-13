"""Unit tests for DetailedWordStore payload validation in get_or_extract_details()."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_exceptions import PayloadValidationError
from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from tests.unit.database.mock_backend import MockBackend


class FakeValidator:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, int, dict]] = []
        self._error = error

    def validate_payload(self, schema_key: str, schema_version: int, payload: dict) -> None:
        self.calls.append((schema_key, schema_version, payload))
        if self._error is not None:
            raise self._error


class FakeExtractor:
    """Mock extractor for testing."""

    def __init__(self, results: list[DetailedWordRecord]) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


class TestDetailedWordStoreValidationExtract:
    """Test DetailedWordStore validation in get_or_extract_details()."""

    @pytest.fixture
    def backend(self) -> MockBackend:
        """Create a mock backend for testing."""
        return MockBackend()

    @pytest.fixture
    def validator(self) -> FakeValidator:
        """Create a fake validator for testing."""
        return FakeValidator()

    @pytest.fixture
    def store_with_extractor_and_validator(
        self, backend: MockBackend, validator: FakeValidator
    ) -> tuple[DetailedWordStore, FakeExtractor, FakeValidator]:
        """Create a DetailedWordStore with extractor and validator."""
        extractor = FakeExtractor([])
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
            extractor=extractor,
            payload_validator=validator,
        )
        return store, extractor, validator

    async def test_get_or_extract_details_validator_called_on_extraction(
        self,
        store_with_extractor_and_validator: tuple[DetailedWordStore, FakeExtractor, FakeValidator],
        backend: MockBackend,
    ) -> None:
        """Test get_or_extract_details on extraction path - validator called for extracted records."""
        store, extractor, validator = store_with_extractor_and_validator

        # Add word to corpus
        word_id = await backend.add_word("nl", "kat", "noun")
        assert word_id is not None

        # Configure extractor to return detailed record
        payload = {"article": "de", "plural": "katten"}
        extracted_record = DetailedWordRecord(
            source_word="kat",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload=payload,
        )
        extractor._results = [extracted_record]

        word = Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await store.get_or_extract_details([word])

        # Verify result
        assert len(result) == 1
        assert result[0].source_word == "kat"

        # Verify validator was called for extracted record (once on extract, once on read)
        assert len(validator.calls) == 2
        assert validator.calls[0] == ("nl_ru_noun", 1, payload)  # On extraction
        assert validator.calls[1] == ("nl_ru_noun", 1, payload)  # On read

    async def test_get_or_extract_details_validator_error_on_extraction_propagates_and_not_persisted(
        self,
        store_with_extractor_and_validator: tuple[DetailedWordStore, FakeExtractor, FakeValidator],
        backend: MockBackend,
    ) -> None:
        """Test get_or_extract_details validator error on extraction - error propagates, record NOT persisted."""
        store, extractor, _ = store_with_extractor_and_validator

        # Create validator that raises error
        error_validator = FakeValidator(PayloadValidationError("Invalid extracted payload"))
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
            extractor=extractor,
            payload_validator=error_validator,
        )

        # Add word to corpus
        word_id = await backend.add_word("nl", "kat", "noun")
        assert word_id is not None

        # Configure extractor to return detailed record
        payload = {"invalid": "extracted_data"}
        extracted_record = DetailedWordRecord(
            source_word="kat",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload=payload,
        )
        extractor._results = [extracted_record]

        word = Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL)

        # Verify error propagates
        with pytest.raises(PayloadValidationError, match="Invalid extracted payload"):
            await store.get_or_extract_details([word])

        # Verify record was NOT persisted (upsert was not called for that record)
        detail_row = await backend.get_word_details("word_details_nl_ru", word_id, "noun")
        assert detail_row is None

    async def test_get_or_extract_details_validator_on_read_path_existing_records(
        self,
        store_with_extractor_and_validator: tuple[DetailedWordStore, FakeExtractor, FakeValidator],
        backend: MockBackend,
    ) -> None:
        """Test get_or_extract_details validator on read path for existing records."""
        store, extractor, validator = store_with_extractor_and_validator

        # Add word to corpus
        word_id = await backend.add_word("nl", "hond", "noun")
        assert word_id is not None

        # Add existing detailed record
        payload = {"article": "de", "plural": "honden"}
        await backend.upsert_word_details("word_details_nl_ru", word_id, "noun", "nl_ru_noun", 1, json.dumps(payload))

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await store.get_or_extract_details([word])

        # Verify result
        assert len(result) == 1
        assert result[0].source_word == "hond"

        # Verify validator was called for existing record
        assert len(validator.calls) == 1
        assert validator.calls[0] == ("nl_ru_noun", 1, payload)

        # Verify extractor was NOT called (existing record)
        assert len(extractor.extract_calls) == 0
