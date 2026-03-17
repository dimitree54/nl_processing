"""Integration tests for DetailedWordStore read-only workflows against real Neon."""

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.detailed_models import DetailedWordRecord
from nl_processing.database.detailed_store import DetailedWordStore
from tests.integration.database.conftest import (
    make_seeded_word_set,
    make_unique_user_id,
    seed_detail,
)
from tests.integration.database.fake_extractor import FakeExtractor


@pytest.mark.asyncio
async def test_get_details_readonly_access(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
    seed_detail: seed_detail,
) -> None:
    """get_details provides read-only access to persisted records."""
    user_id = make_unique_user_id()

    # Seed source words
    word_specs = [
        ("readonly1", None, PartOfSpeech.NOUN),
        ("readonly2", None, PartOfSpeech.VERB),
    ]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Seed details for both words
    await seed_detail(
        source_word_id=pairs[0].source_word_id,
        word_type=PartOfSpeech.NOUN,
        schema_key="nl_ru_noun",
        schema_version=1,
        payload={"article": "de", "type": "concrete"},
    )
    await seed_detail(
        source_word_id=pairs[1].source_word_id,
        word_type=PartOfSpeech.VERB,
        schema_key="nl_ru_verb",
        schema_version=1,
        payload={"infinitive": "readonly2", "conjugation": "regular"},
    )

    # Create store without extractor
    store = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
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

    # Read details
    result = await store.get_details(words)

    assert len(result) == 2
    result_by_word = {r.source_word: r for r in result}

    assert result_by_word["readonly1"].payload["type"] == "concrete"
    assert result_by_word["readonly2"].payload["conjugation"] == "regular"


@pytest.mark.asyncio
async def test_persistence_across_store_instances(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """Details extracted by one store instance persist for other instances."""
    user_id = make_unique_user_id()

    # Seed source word
    word_specs = [("persistent", None, PartOfSpeech.NOUN)]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Store 1: extract and persist
    extracted_records = [
        DetailedWordRecord(
            source_word="persistent",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"note": "extracted by store 1"},
        )
    ]
    extractor1 = FakeExtractor(extracted_records)

    store1 = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
        extractor=extractor1,
    )

    word = Word(
        normalized_form=pairs[0].source_normalized_form,
        word_type=pairs[0].word_type,
        language=Language.NL,
    )

    await store1.get_or_extract_details([word])

    # Store 2: read-only, should find persisted data
    store2 = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
    )

    result = await store2.get_details([word])
    assert len(result) == 1
    assert result[0].payload["note"] == "extracted by store 1"


@pytest.mark.asyncio
async def test_get_or_extract_all_hits_no_extraction(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
    seed_detail: seed_detail,
) -> None:
    """get_or_extract_details does not call extractor when all records exist."""
    user_id = make_unique_user_id()

    # Seed source word
    word_specs = [("existing", None, PartOfSpeech.NOUN)]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Pre-seed detail
    await seed_detail(
        source_word_id=pairs[0].source_word_id,
        word_type=PartOfSpeech.NOUN,
        schema_key="nl_ru_noun",
        schema_version=1,
        payload={"article": "de", "meaning": "existing thing"},
    )

    # Prepare extractor (should not be called)
    extractor = FakeExtractor([])

    store = DetailedWordStore(
        source_language=Language.NL,
        target_language=Language.RU,
        backend=neon_backend,
        extractor=extractor,
    )

    # Convert to Word object
    words = [
        Word(
            normalized_form=pairs[0].source_normalized_form,
            word_type=pairs[0].word_type,
            language=Language.NL,
        )
    ]

    # Call get_or_extract_details
    result = await store.get_or_extract_details(words)

    # Verify no extraction calls
    assert len(extractor.extract_calls) == 0

    # Verify result from existing record
    assert len(result) == 1
    assert result[0].source_word == "existing"
    assert result[0].payload["meaning"] == "existing thing"
