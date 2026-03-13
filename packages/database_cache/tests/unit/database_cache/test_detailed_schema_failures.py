"""Tests for DetailedWordCacheService schema validation and failure handling."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.detailed_models import DetailedWordRecord
import pytest

from nl_processing.database_cache._detailed_local_store import DetailedLocalStore
from nl_processing.database_cache.detailed_cache import DetailedWordCacheService
from tests.unit.database_cache.detailed_mocks import MockRemoteDetailedWordStore, MockSchemaChecker


@pytest.mark.asyncio
async def test_schema_version_invalidation() -> None:
    """Test that incompatible schema versions are invalidated and re-fetched."""
    local_store = DetailedLocalStore(":memory:")
    await local_store.open()

    # Pre-populate cache with "incompatible" version
    await local_store.upsert_cached_detail("huis", "noun", "nl_ru_noun", 1, json.dumps({"definition": "old_house"}))

    # Create schema checker that marks version 1 as incompatible
    schema_checker = MockSchemaChecker({"nl_ru_noun": [2]})  # Only version 2 is compatible

    # Create mock remote with updated record
    remote_record = DetailedWordRecord(
        source_word="huis",
        word_type="noun",
        schema_key="nl_ru_noun",
        schema_version=2,
        payload={"definition": "new_house"},
    )
    mock_remote = MockRemoteDetailedWordStore([remote_record])

    service = DetailedWordCacheService(
        Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store, schema_checker=schema_checker
    )

    words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    result = await service.get_or_fetch_details(words)

    assert len(result) == 1
    assert result[0].source_word == "huis"
    assert result[0].payload == {"definition": "new_house"}  # Should get updated record
    assert result[0].schema_version == 2

    # Verify old record was deleted and new one cached
    cached = await local_store.get_cached_detail("huis", "noun")
    assert cached is not None
    assert cached["schema_version"] == 2
    assert json.loads(cached["payload"]) == {"definition": "new_house"}


@pytest.mark.asyncio
async def test_remote_failure_preserves_local_state() -> None:
    """Test that remote failures leave local cache unchanged."""
    local_store = DetailedLocalStore(":memory:")
    await local_store.open()

    # Pre-populate cache
    await local_store.upsert_cached_detail(
        "existing", "noun", "nl_ru_noun", 1, json.dumps({"definition": "existing_word"})
    )

    # Create mock remote that raises an error
    mock_remote = MockRemoteDetailedWordStore()
    mock_remote.error_to_raise = RuntimeError("Remote service failed")

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    words = [Word(normalized_form="missing", word_type=PartOfSpeech.NOUN, language=Language.NL)]

    # Remote failure should propagate
    with pytest.raises(RuntimeError, match="Remote service failed"):
        await service.get_or_fetch_details(words)

    # Local state should be unchanged
    cached = await local_store.get_cached_detail("existing", "noun")
    assert cached is not None
    assert cached["source_word"] == "existing"

    # New record should not be in cache
    missing_cached = await local_store.get_cached_detail("missing", "noun")
    assert missing_cached is None


@pytest.mark.asyncio
async def test_order_preservation() -> None:
    """Test that results are returned in the same order as input."""
    local_store = DetailedLocalStore(":memory:")

    # Create remote records
    records = [
        DetailedWordRecord(
            source_word="alpha",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"definition": "alpha_def"},
        ),
        DetailedWordRecord(
            source_word="beta",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"definition": "beta_def"},
        ),
        DetailedWordRecord(
            source_word="gamma",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"definition": "gamma_def"},
        ),
    ]
    mock_remote = MockRemoteDetailedWordStore(records)

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    # Request words in specific order
    words = [
        Word(normalized_form="gamma", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="alpha", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="beta", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    result = await service.get_or_fetch_details(words)

    assert len(result) == 3
    assert result[0].source_word == "gamma"
    assert result[1].source_word == "alpha"
    assert result[2].source_word == "beta"


@pytest.mark.asyncio
async def test_partial_results_when_remote_returns_fewer() -> None:
    """Test that service handles when remote returns fewer results than requested."""
    local_store = DetailedLocalStore(":memory:")

    # Create remote records for only 2 out of 3 words
    records = [
        DetailedWordRecord(
            source_word="alpha",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"definition": "alpha_def"},
        ),
        DetailedWordRecord(
            source_word="gamma",
            word_type="noun",
            schema_key="nl_ru_noun",
            schema_version=1,
            payload={"definition": "gamma_def"},
        ),
        # Note: no record for "beta"
    ]
    mock_remote = MockRemoteDetailedWordStore(records)

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    # Request 3 words but only 2 have remote records
    words = [
        Word(normalized_form="alpha", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="beta", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="gamma", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]

    result = await service.get_or_fetch_details(words)

    # Should get 2 results (alpha and gamma), beta is skipped
    assert len(result) == 2
    assert result[0].source_word == "alpha"
    assert result[1].source_word == "gamma"
