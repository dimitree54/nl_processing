"""Unit tests for DetailedWordStore.get_or_extract_details()."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_exceptions import SourceWordNotFoundError
from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from tests.unit.database.mock_backend import MockBackend


class FakeExtractor:
    """Mock extractor for testing."""

    def __init__(self, results: list[DetailedWordRecord]) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


class TestDetailedWordStoreExtract:
    """Test DetailedWordStore.get_or_extract_details functionality."""

    @pytest.fixture
    def backend(self) -> MockBackend:
        """Create a mock backend for testing."""
        return MockBackend()

    @pytest.fixture
    def store(self, backend: MockBackend) -> DetailedWordStore:
        """Create a DetailedWordStore with mock backend."""
        return DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
        )

    @pytest.fixture
    def extractor_store(self, backend: MockBackend) -> tuple[DetailedWordStore, FakeExtractor]:
        """Create a DetailedWordStore with mock backend and extractor."""
        extractor = FakeExtractor([])
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
            extractor=extractor,
        )
        return store, extractor

    async def test_get_or_extract_details_empty_input(
        self, extractor_store: tuple[DetailedWordStore, FakeExtractor]
    ) -> None:
        """Test get_or_extract_details with empty input returns empty list."""
        store, extractor = extractor_store
        result = await store.get_or_extract_details([])
        assert result == []
        assert extractor.extract_calls == []

    async def test_get_or_extract_details_without_extractor(self, store: DetailedWordStore) -> None:
        """Test get_or_extract_details without extractor raises ValueError."""
        word = Word(normalized_form="test", word_type=PartOfSpeech.NOUN, language=Language.NL)

        with pytest.raises(ValueError, match="get_or_extract_details requires an extractor"):
            await store.get_or_extract_details([word])

    async def test_get_or_extract_details_word_not_in_corpus(
        self, extractor_store: tuple[DetailedWordStore, FakeExtractor]
    ) -> None:
        """Test get_or_extract_details raises SourceWordNotFoundError for unknown word."""
        store, _ = extractor_store
        word = Word(normalized_form="unknown", word_type=PartOfSpeech.NOUN, language=Language.NL)

        with pytest.raises(SourceWordNotFoundError, match="Source word 'unknown' not found"):
            await store.get_or_extract_details([word])

    async def test_get_or_extract_details_all_hits_no_extraction(
        self, extractor_store: tuple[DetailedWordStore, FakeExtractor], backend: MockBackend
    ) -> None:
        """Test get_or_extract_details with all hits does not call extractor."""
        store, extractor = extractor_store

        # Add word to corpus
        word_id = await backend.add_word("nl", "hond", "noun")
        assert word_id is not None

        # Add detailed record
        payload = {"article": "de"}
        await backend.upsert_word_details("word_details_nl_ru", word_id, "noun", "nl_ru_noun", 1, json.dumps(payload))

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await store.get_or_extract_details([word])

        assert len(result) == 1
        assert result[0].source_word == "hond"
        assert extractor.extract_calls == []  # No extraction needed

    async def test_get_or_extract_details_all_misses_calls_extractor(
        self, extractor_store: tuple[DetailedWordStore, FakeExtractor], backend: MockBackend
    ) -> None:
        """Test get_or_extract_details with all misses calls extractor and persists."""
        store, extractor = extractor_store

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

        # Verify extractor was called
        assert len(extractor.extract_calls) == 1
        assert extractor.extract_calls[0] == [word]

        # Verify result
        assert len(result) == 1
        assert result[0].source_word == "kat"
        assert result[0].payload == payload

        # Verify persisted
        detail_row = await backend.get_word_details("word_details_nl_ru", word_id, "noun")
        assert detail_row is not None
        assert detail_row["schema_key"] == "nl_ru_noun"

    async def test_get_or_extract_details_mixed_hits_and_misses(
        self, extractor_store: tuple[DetailedWordStore, FakeExtractor], backend: MockBackend
    ) -> None:
        """Test get_or_extract_details with mix of hits and misses."""
        store, extractor = extractor_store

        # Add two words to corpus
        word_id1 = await backend.add_word("nl", "hond", "noun")
        word_id2 = await backend.add_word("nl", "kat", "noun")
        assert word_id1 is not None and word_id2 is not None

        # Add detail for first word only
        payload1 = {"article": "de", "plural": "honden"}
        await backend.upsert_word_details("word_details_nl_ru", word_id1, "noun", "nl_ru_noun", 1, json.dumps(payload1))

        # Configure extractor for second word
        payload2 = {"article": "de", "plural": "katten"}
        extracted_record = DetailedWordRecord(
            source_word="kat",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload=payload2,
        )
        extractor._results = [extracted_record]

        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        result = await store.get_or_extract_details(words)

        # Verify extractor called only for missing word
        assert len(extractor.extract_calls) == 1
        assert len(extractor.extract_calls[0]) == 1
        assert extractor.extract_calls[0][0].normalized_form == "kat"

        # Verify results in input order
        assert len(result) == 2
        assert result[0].source_word == "hond"
        assert result[0].payload == payload1
        assert result[1].source_word == "kat"
        assert result[1].payload == payload2
