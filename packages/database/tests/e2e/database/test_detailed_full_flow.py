"""E2E tests for DetailedWordStore end-to-end workflows."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import reset_test_database


class FakeExtractor:
    """Mock extractor for E2E testing."""

    def __init__(self, results: list[DetailedWordRecord]) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


@pytest.fixture(autouse=True)
async def reset_db() -> None:
    """Reset test database before each test."""
    await reset_test_database()


class TestDetailedStoreE2E:
    """E2E tests for DetailedWordStore workflows."""

    async def test_full_workflow_add_extract_read_again(self) -> None:
        """Test full workflow: add words, extract details, read again without re-extraction."""
        # Step 1: Create service and store
        service = DatabaseService(user_id="test_user")
        await service.create_tables(exercise_slugs=["translation"])

        # Step 2: Add source words to corpus
        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        ]
        result = await service.add_words(words)
        assert len(result.new_words) == 2

        # Step 3: Set up extractor with expected results
        extracted_records = [
            DetailedWordRecord(
                source_word="hond",
                word_type="noun",
                schema_key="nl_ru_noun",
                schema_version=1,
                payload={"article": "de", "plural": "honden", "gender": "masculine"},
            ),
            DetailedWordRecord(
                source_word="lopen",
                word_type="verb",
                schema_key="nl_ru_verb",
                schema_version=1,
                payload={"infinitive": "lopen", "past_tense": "liep", "past_participle": "gelopen"},
            ),
        ]
        extractor = FakeExtractor(extracted_records)

        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            extractor=extractor,
        )

        # Step 4: First call to get_or_extract_details - should extract
        first_result = await store.get_or_extract_details(words)

        # Verify extractor was called
        assert len(extractor.extract_calls) == 1
        assert len(extractor.extract_calls[0]) == 2

        # Verify results
        assert len(first_result) == 2
        assert first_result[0].source_word == "hond"
        assert first_result[0].payload["article"] == "de"
        assert first_result[1].source_word == "lopen"
        assert first_result[1].payload["infinitive"] == "lopen"

        # Step 5: Second call to get_or_extract_details - should NOT re-extract
        extractor.extract_calls.clear()
        second_result = await store.get_or_extract_details(words)

        # Verify no re-extraction
        assert len(extractor.extract_calls) == 0

        # Verify same results
        assert len(second_result) == 2
        assert second_result[0].source_word == "hond"
        assert second_result[0].payload["article"] == "de"
        assert second_result[1].source_word == "lopen"
        assert second_result[1].payload["infinitive"] == "lopen"

        # Step 6: Test get_details also works (without extractor dependency)
        store_without_extractor = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
        )

        third_result = await store_without_extractor.get_details(words)
        assert len(third_result) == 2
        assert third_result[0].payload["plural"] == "honden"
        assert third_result[1].payload["past_tense"] == "liep"

    async def test_partial_extraction_workflow(self) -> None:
        """Test workflow with mix of existing and new words requiring extraction."""
        # Setup
        service = DatabaseService(user_id="test_user")
        await service.create_tables(exercise_slugs=["translation"])

        # Add words to corpus
        words = [
            Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="boom", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        await service.add_words(words)

        # Pre-populate detail for first word
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        backend = store._backend
        huis_word = await backend.get_word("nl", "huis")
        assert huis_word is not None
        await backend.upsert_word_details(
            "word_details_nl_ru",
            int(huis_word["id"]),
            "noun",
            "nl_ru_noun",
            1,
            '{"article": "het", "plural": "huizen"}',
        )

        # Set up extractor for remaining words
        extracted_records = [
            DetailedWordRecord(
                source_word="boom",
                word_type="noun",
                schema_key="nl_ru_noun",
                schema_version=1,
                payload={"article": "de", "plural": "bomen"},
            ),
            DetailedWordRecord(
                source_word="water",
                word_type="noun",
                schema_key="nl_ru_noun",
                schema_version=1,
                payload={"article": "het", "plural": "waters"},
            ),
        ]
        extractor = FakeExtractor(extracted_records)

        store_with_extractor = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            extractor=extractor,
        )

        # Call get_or_extract_details
        result = await store_with_extractor.get_or_extract_details(words)

        # Verify extractor called only for missing words
        assert len(extractor.extract_calls) == 1
        extracted_words = extractor.extract_calls[0]
        assert len(extracted_words) == 2
        extracted_forms = {w.normalized_form for w in extracted_words}
        assert extracted_forms == {"boom", "water"}

        # Verify all results returned in order
        assert len(result) == 3
        assert result[0].source_word == "huis"
        assert result[0].payload["article"] == "het"
        assert result[1].source_word == "boom"
        assert result[1].payload["article"] == "de"
        assert result[2].source_word == "water"
        assert result[2].payload["plural"] == "waters"

    async def test_empty_input_handling(self) -> None:
        """Test that empty inputs are handled correctly throughout the workflow."""
        service = DatabaseService(user_id="test_user")
        await service.create_tables(exercise_slugs=["translation"])

        extractor = FakeExtractor([])
        store = DetailedWordStore(source_language=Language.NL, target_language=Language.RU, extractor=extractor)

        # Test empty inputs
        assert await store.get_details([]) == []
        assert await store.get_or_extract_details([]) == []
        assert len(extractor.extract_calls) == 0
