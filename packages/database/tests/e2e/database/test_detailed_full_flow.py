"""E2E tests for DetailedWordStore end-to-end workflows."""

from collections.abc import AsyncIterator
import os

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import drop_all_tables, reset_database


class FakeExtractor:
    """Mock extractor for E2E testing."""

    def __init__(self, results: list[DetailedWordRecord]) -> None:
        self.extract_calls: list[list[Word]] = []
        self._results = results

    async def extract(self, words: list[Word]) -> list[DetailedWordRecord]:
        self.extract_calls.append(words)
        return self._results


_LANGUAGES = ["nl", "ru"]
_PAIRS = [("nl", "ru")]
_EXERCISE_SLUGS = ["translation"]


@pytest.fixture
async def backend() -> AsyncIterator[NeonBackend]:
    """Shared backend for all stores in the test — single Neon connection."""
    b = NeonBackend(os.environ["DATABASE_URL"])
    conn = await b._connect()  # noqa: SLF001
    await conn.execute("SELECT pg_advisory_lock(12345)")
    try:
        await reset_database(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS, backend=b)
        yield b
        await drop_all_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS, backend=b)
        await b.create_tables(_LANGUAGES, _PAIRS, _EXERCISE_SLUGS)
    finally:
        await conn.execute("SELECT pg_advisory_unlock(12345)")


class TestDetailedStoreE2E:
    """E2E tests for DetailedWordStore workflows."""

    async def test_full_workflow_add_extract_read_again(self, backend: NeonBackend) -> None:
        """Test full workflow: add words, extract details, read again without re-extraction."""
        service = DatabaseService(user_id="test_user", backend=backend)
        await service.create_tables(exercise_slugs=_EXERCISE_SLUGS)

        words = [
            Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        ]
        result = await service.add_words(words)
        assert len(result.new_words) == 2

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
            backend=backend,
            extractor=extractor,
        )

        # First call — should extract
        first_result = await store.get_or_extract_details(words)
        assert len(extractor.extract_calls) == 1
        assert len(extractor.extract_calls[0]) == 2
        assert len(first_result) == 2
        assert first_result[0].source_word == "hond"
        assert first_result[0].payload["article"] == "de"
        assert first_result[1].source_word == "lopen"
        assert first_result[1].payload["infinitive"] == "lopen"

        # Second call — should NOT re-extract
        extractor.extract_calls.clear()
        second_result = await store.get_or_extract_details(words)
        assert len(extractor.extract_calls) == 0
        assert len(second_result) == 2
        assert second_result[0].source_word == "hond"
        assert second_result[1].source_word == "lopen"

        # Read-only store (no extractor) — same backend, should find persisted data
        store_readonly = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
        )
        third_result = await store_readonly.get_details(words)
        assert len(third_result) == 2
        assert third_result[0].payload["plural"] == "honden"
        assert third_result[1].payload["past_tense"] == "liep"

    async def test_partial_extraction_workflow(self, backend: NeonBackend) -> None:
        """Test workflow with mix of existing and new words requiring extraction."""
        service = DatabaseService(user_id="test_user", backend=backend)
        await service.create_tables(exercise_slugs=_EXERCISE_SLUGS)

        words = [
            Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="boom", word_type=PartOfSpeech.NOUN, language=Language.NL),
            Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
        ]
        await service.add_words(words)

        # Pre-populate detail for first word
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

        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
            extractor=extractor,
        )

        result = await store.get_or_extract_details(words)

        assert len(extractor.extract_calls) == 1
        extracted_words = extractor.extract_calls[0]
        assert len(extracted_words) == 2
        extracted_forms = {w.normalized_form for w in extracted_words}
        assert extracted_forms == {"boom", "water"}

        assert len(result) == 3
        assert result[0].source_word == "huis"
        assert result[0].payload["article"] == "het"
        assert result[1].source_word == "boom"
        assert result[1].payload["article"] == "de"
        assert result[2].source_word == "water"
        assert result[2].payload["plural"] == "waters"

    async def test_empty_input_handling(self, backend: NeonBackend) -> None:
        """Test that empty inputs are handled correctly throughout the workflow."""
        service = DatabaseService(user_id="test_user", backend=backend)
        await service.create_tables(exercise_slugs=_EXERCISE_SLUGS)

        extractor = FakeExtractor([])
        store = DetailedWordStore(
            source_language=Language.NL,
            target_language=Language.RU,
            backend=backend,
            extractor=extractor,
        )

        assert await store.get_details([]) == []
        assert await store.get_or_extract_details([]) == []
        assert len(extractor.extract_calls) == 0
