"""Tests for DetailedWordCacheService cache hits and misses."""

import json

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.detailed_models import DetailedWordRecord
import pytest

from nl_processing.database_cache._detailed_local_store import DetailedLocalStore
from nl_processing.database_cache.detailed_cache import DetailedWordCacheService
from tests.unit.database_cache.detailed_mocks import MockRemoteDetailedWordStore


@pytest.mark.asyncio
async def test_get_or_fetch_details_all_hits() -> None:
    """Test that all cache hits don't call remote store."""
    # Create a local store with cached data
    local_store = DetailedLocalStore(":memory:")
    await local_store.open()

    # Pre-populate cache
    record_data = {
        "source_word": "huis",
        "word_type": "noun",
        "schema_key": "nl_ru_noun",
        "schema_version": 1,
        "payload": {"definition": "house"},
    }

    await local_store.upsert_cached_detail(
        record_data["source_word"],
        record_data["word_type"],
        record_data["schema_key"],
        record_data["schema_version"],
        json.dumps(record_data["payload"]),
    )

    # Create mock remote (should not be called)
    mock_remote = MockRemoteDetailedWordStore()

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    result = await service.get_or_fetch_details(words)

    assert len(result) == 1
    assert result[0].source_word == "huis"
    assert result[0].word_type == "noun"
    assert result[0].payload == {"definition": "house"}
    assert mock_remote.called_with is None  # Remote not called


@pytest.mark.asyncio
async def test_get_or_fetch_details_all_misses() -> None:
    """Test that cache misses call remote store and cache results."""
    local_store = DetailedLocalStore(":memory:")

    # Create mock remote with test data
    remote_record = DetailedWordRecord(
        source_word="tafel",
        word_type="noun",
        schema_key="nl_ru_noun",
        schema_version=1,
        payload={"definition": "table"},
    )
    mock_remote = MockRemoteDetailedWordStore([remote_record])

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    words = [Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    result = await service.get_or_fetch_details(words)

    assert len(result) == 1
    assert result[0].source_word == "tafel"
    assert result[0].word_type == "noun"
    assert result[0].payload == {"definition": "table"}

    # Verify remote was called
    assert mock_remote.called_with is not None
    assert len(mock_remote.called_with) == 1
    assert mock_remote.called_with[0][0].normalized_form == "tafel"

    # Verify result was cached
    cached = await local_store.get_cached_detail("tafel", "noun")
    assert cached is not None
    assert cached["source_word"] == "tafel"


@pytest.mark.asyncio
async def test_get_or_fetch_details_mixed_hits_and_misses() -> None:
    """Test mixed cache hits and misses."""
    local_store = DetailedLocalStore(":memory:")
    await local_store.open()

    # Pre-populate cache with one record
    await local_store.upsert_cached_detail("huis", "noun", "nl_ru_noun", 1, json.dumps({"definition": "house"}))

    # Create mock remote with another record
    remote_record = DetailedWordRecord(
        source_word="tafel",
        word_type="noun",
        schema_key="nl_ru_noun",
        schema_version=1,
        payload={"definition": "table"},
    )
    mock_remote = MockRemoteDetailedWordStore([remote_record])

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    words = [
        Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    result = await service.get_or_fetch_details(words)

    assert len(result) == 2

    # Results should be in the same order as input
    assert result[0].source_word == "huis"
    assert result[0].payload == {"definition": "house"}
    assert result[1].source_word == "tafel"
    assert result[1].payload == {"definition": "table"}

    # Remote should only be called for the miss
    assert mock_remote.called_with is not None
    assert len(mock_remote.called_with[0]) == 1
    assert mock_remote.called_with[0][0].normalized_form == "tafel"
