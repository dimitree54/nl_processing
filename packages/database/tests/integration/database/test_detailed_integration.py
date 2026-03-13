"""Integration tests for DetailedWordStore with real Neon DB."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.detailed_exceptions import SourceWordNotFoundError
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database.service import DatabaseService


class TestDetailedWordStoreIntegration:
    """Integration tests for DetailedWordStore."""

    async def test_create_tables_creates_detailed_table(self, neon_backend: NeonBackend) -> None:
        """Test that create_tables creates word_details table."""
        # Verify we can use the detailed store without errors
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=neon_backend,
        )

        result = await store.get_details([])
        assert result == []

    async def test_round_trip_persistence(self, neon_backend: NeonBackend) -> None:
        """Test persisting and reading back detailed word record."""
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=neon_backend,
        )

        # Add word to corpus
        service = DatabaseService(user_id="test_user", backend=neon_backend)
        words = [Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)]
        await service.add_words(words)

        # Create and add a detailed record
        word = Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)
        payload = {"article": "de", "plural": "honden", "gender": "masculine"}

        # Get the backend for direct persistence
        backend = store._backend
        source_word = await backend.get_word("nl", "hond")
        assert source_word is not None
        source_word_id = int(source_word["id"])

        # Persist detail
        await backend.upsert_word_details(
            "word_details_nl_ru",
            source_word_id,
            "noun",
            "nl_ru_noun_v2",
            2,
            json.dumps(payload),
        )

        # Read back via store
        result = await store.get_details([word])
        assert len(result) == 1
        assert result[0].source_word == "hond"
        assert result[0].word_type == "noun"
        assert result[0].schema_key == "nl_ru_noun_v2"
        assert result[0].schema_version == 2
        assert result[0].payload == payload

    async def test_get_details_with_missing_word(self, neon_backend: NeonBackend) -> None:
        """Test get_details with word not in corpus raises error."""
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=neon_backend,
        )

        unknown_word = Word(normalized_form="unknown", word_type=PartOfSpeech.NOUN, language=Language.NL)

        with pytest.raises(SourceWordNotFoundError):
            await store.get_details([unknown_word])

    async def test_batch_queries_work(self, neon_backend: NeonBackend) -> None:
        """Test that batch queries work correctly."""
        # Add words to corpus
        service = DatabaseService(user_id="test_user", backend=neon_backend)
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        await service.add_words(words)

        # Get source word IDs
        hond_word = await neon_backend.get_word("nl", "hond")
        kat_word = await neon_backend.get_word("nl", "kat")
        assert hond_word is not None and kat_word is not None

        hond_id = int(hond_word["id"])
        kat_id = int(kat_word["id"])

        # Persist details for both words
        await neon_backend.upsert_word_details(
            "word_details_nl_ru",
            hond_id,
            "noun",
            "nl_ru_noun",
            1,
            '{"article": "de"}',
        )
        await neon_backend.upsert_word_details(
            "word_details_nl_ru",
            kat_id,
            "noun",
            "nl_ru_noun",
            1,
            '{"article": "de"}',
        )

        # Test batch query
        ids_and_types = [(hond_id, "noun"), (kat_id, "noun")]
        results = await neon_backend.get_word_details_batch("word_details_nl_ru", ids_and_types)

        assert len(results) == 2
        source_words = {int(row["source_word_id"]): row for row in results}
        assert hond_id in source_words
        assert kat_id in source_words

    async def test_upsert_updates_existing_record(self, neon_backend: NeonBackend) -> None:
        """Test that upsert updates existing records instead of creating duplicates."""
        # Add word to corpus
        service = DatabaseService(user_id="test_user", backend=neon_backend)
        words = [Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)]
        await service.add_words(words)

        hond_word = await neon_backend.get_word("nl", "hond")
        assert hond_word is not None
        hond_id = int(hond_word["id"])

        # Initial persistence
        await neon_backend.upsert_word_details(
            "word_details_nl_ru",
            hond_id,
            "noun",
            "nl_ru_noun",
            1,
            '{"article": "de", "status": "initial"}',
        )

        # Update with new data
        await neon_backend.upsert_word_details(
            "word_details_nl_ru",
            hond_id,
            "noun",
            "nl_ru_noun_v2",
            2,
            '{"article": "de", "status": "updated", "plural": "honden"}',
        )

        # Verify only one record exists with updated data
        result = await neon_backend.get_word_details("word_details_nl_ru", hond_id, "noun")
        assert result is not None
        assert result["schema_key"] == "nl_ru_noun_v2"
        assert result["schema_version"] == 2
        payload_raw = result["payload"]
        # Handle both string and dict payloads (asyncpg behavior can vary)
        if isinstance(payload_raw, str):
            payload = json.loads(payload_raw)
        else:
            payload = payload_raw
        assert payload["status"] == "updated"
        assert payload["plural"] == "honden"
