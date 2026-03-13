"""Unit tests for DetailedWordStore.get_details()."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_exceptions import SourceWordNotFoundError
from nl_processing.database.detailed_store import DetailedWordStore
from tests.unit.database.conftest import add_word_with_detail
from tests.unit.database.mock_backend import MockBackend


class TestDetailedWordStoreGetDetails:
    """Test DetailedWordStore.get_details functionality."""

    async def test_get_details_empty_input(self, detailed_store: DetailedWordStore) -> None:
        """Test get_details with empty input returns empty list."""
        result = await detailed_store.get_details([])
        assert result == []

    async def test_get_details_word_not_in_corpus(self, detailed_store: DetailedWordStore) -> None:
        """Test get_details raises SourceWordNotFoundError for unknown word."""
        word = Word(normalized_form="unknown", word_type=PartOfSpeech.NOUN, language=Language.NL)

        with pytest.raises(SourceWordNotFoundError, match="Source word 'unknown' not found"):
            await detailed_store.get_details([word])

    async def test_get_details_word_in_corpus_no_details(
        self, detailed_store: DetailedWordStore, detailed_backend: MockBackend
    ) -> None:
        """Test get_details with word in corpus but no details returns empty list."""
        # Add word to corpus
        word_id = await detailed_backend.add_word("nl", "hond", "noun")
        assert word_id is not None

        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await detailed_store.get_details([word])
        assert result == []

    async def test_get_details_word_with_existing_details(
        self, detailed_store: DetailedWordStore, detailed_backend: MockBackend
    ) -> None:
        """Test get_details returns existing detailed record."""
        word_id, payload = await add_word_with_detail(detailed_backend)
        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        result = await detailed_store.get_details([word])

        assert len(result) == 1
        assert result[0].source_word == "hond"
        assert result[0].word_type == "noun"
        assert result[0].schema_key == "nl_ru_noun"
        assert result[0].schema_version == 1
        assert result[0].payload == payload

    async def test_get_details_multiple_words_mixed_results(
        self, detailed_store: DetailedWordStore, detailed_backend: MockBackend
    ) -> None:
        """Test get_details with multiple words, some with details, some without."""
        # Add first word with detail
        _, payload1 = await add_word_with_detail(detailed_backend, "hond")

        # Add second word (no detail)
        word_id2 = await detailed_backend.add_word("nl", "kat", "noun")
        assert word_id2 is not None

        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        result = await detailed_store.get_details(words)

        # Only the first word should have details
        assert len(result) == 1
        assert result[0].source_word == "hond"
        assert result[0].payload == payload1
