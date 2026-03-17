"""Integration tests for DetailedWordStore extraction workflows against real Neon."""

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from nl_processing.database.service import DatabaseService
from tests.integration.database.conftest import (
    make_seeded_word_set,
    make_unique_user_id,
    seed_detail,
)
from tests.integration.database.fake_extractor import FakeExtractor
from tests.integration.database.seed_helpers import make_unique_word_form


@pytest.mark.asyncio
async def test_get_or_extract_all_misses_calls_extractor(
    neon_backend: NeonBackend,
) -> None:
    """get_or_extract_details calls extractor for all misses and persists results."""
    user_id = make_unique_user_id()

    # Add words to corpus through DatabaseService (no translator to avoid real API calls)
    # Use unique word forms to avoid test contamination
    word_form_1 = make_unique_word_form("hond")
    word_form_2 = make_unique_word_form("kat")

    words = [
        Word(normalized_form=word_form_1, word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form=word_form_2, word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    service = DatabaseService(user_id=user_id, backend=neon_backend)  # No translator
    await service.add_words(words)

    # Prepare fake extractor
    extracted_records = [
        DetailedWordRecord(
            source_word=word_form_1,
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"article": "de", "plural": f"{word_form_1}en"},
        ),
        DetailedWordRecord(
            source_word=word_form_2,
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"article": "de", "plural": f"{word_form_2}en"},
        ),
    ]
    extractor = FakeExtractor(extracted_records)

    store = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
        extractor=extractor,
    )

    # Call get_or_extract_details
    result = await store.get_or_extract_details(words)

    # Verify extractor was called
    assert len(extractor.extract_calls) == 1
    assert len(extractor.extract_calls[0]) == 2

    # Verify results
    assert len(result) == 2
    result_by_word = {r.source_word: r for r in result}

    assert result_by_word[word_form_1].payload["article"] == "de"
    assert result_by_word[word_form_1].payload["plural"] == f"{word_form_1}en"
    assert result_by_word[word_form_2].payload["plural"] == f"{word_form_2}en"


@pytest.mark.asyncio
async def test_get_or_extract_mixed_hits_and_misses(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
    seed_detail: seed_detail,
) -> None:
    """get_or_extract_details extracts only misses when some records exist."""
    user_id = make_unique_user_id()

    # Use unique word forms to avoid test contamination
    word_form_1 = make_unique_word_form("huis")
    word_form_2 = make_unique_word_form("boom")
    word_form_3 = make_unique_word_form("water")

    # Seed three source words
    word_specs = [
        (word_form_1, None, PartOfSpeech.NOUN),
        (word_form_2, None, PartOfSpeech.NOUN),
        (word_form_3, None, PartOfSpeech.NOUN),
    ]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Pre-seed detail for first word
    await seed_detail(
        source_word_id=pairs[0].source_word_id,
        word_type=PartOfSpeech.NOUN,
        schema_key="nl_ru_noun",
        schema_version=1,
        payload={"article": "het", "plural": f"{word_form_1}en"},
    )

    # Prepare extractor for the two missing words
    extracted_records = [
        DetailedWordRecord(
            source_word=word_form_2,
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"article": "de", "plural": f"{word_form_2}en"},
        ),
        DetailedWordRecord(
            source_word=word_form_3,
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"article": "het", "plural": f"{word_form_3}en"},
        ),
    ]
    extractor = FakeExtractor(extracted_records)

    store = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
        extractor=extractor,
    )

    # Convert to Word objects
    words = [
        Word(
            normalized_form=pair.source_normalized_form,
            word_type=pair.word_type,
            language=Language.NL,
        )
        for pair in pairs
    ]

    # Call get_or_extract_details
    result = await store.get_or_extract_details(words)

    # Verify extractor was called only for missing records
    assert len(extractor.extract_calls) == 1
    extracted_forms = {w.normalized_form for w in extractor.extract_calls[0]}
    assert extracted_forms == {word_form_2, word_form_3}

    # Verify all results are returned
    assert len(result) == 3
    result_by_word = {r.source_word: r for r in result}

    # Pre-seeded record
    assert result_by_word[word_form_1].payload["article"] == "het"
    assert result_by_word[word_form_1].payload["plural"] == f"{word_form_1}en"

    # Newly extracted records
    assert result_by_word[word_form_2].payload["article"] == "de"
    assert result_by_word[word_form_3].payload["article"] == "het"
