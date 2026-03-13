"""Integration test for detailed cache lifecycle."""

import pathlib

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database_cache._detailed_local_store import DetailedLocalStore
from nl_processing.database_cache.detailed_cache import DetailedWordCacheService
from tests.integration.database_cache.conftest import make_remote_record
from tests.integration.database_cache.integration_mocks import MockRemoteDetailedWordStore


@pytest.mark.asyncio
async def test_full_lifecycle_cache_empty_to_populated(tmp_path: pathlib.Path) -> None:
    """Test full lifecycle: cache empty → fetch → cache populated → second fetch is a hit."""
    # Create real SQLite file
    db_path = tmp_path / "test_details.db"
    local_store = DetailedLocalStore(str(db_path))

    # Create mock remote with test data
    remote_record = make_remote_record("huis", {"definition": "house", "gender": "neuter"})
    mock_remote = MockRemoteDetailedWordStore([remote_record])

    service = DetailedWordCacheService(Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store)

    word = Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)

    # First call: cache miss, should fetch from remote
    result1 = await service.get_or_fetch_details([word])

    assert len(result1) == 1
    assert result1[0].source_word == "huis"
    assert result1[0].payload == {"definition": "house", "gender": "neuter"}
    assert mock_remote.call_count == 1

    # Verify data was persisted to SQLite
    await local_store.open()
    cached = await local_store.get_cached_detail("huis", "noun")
    assert cached is not None
    assert cached["source_word"] == "huis"
    assert cached["payload"] == '{"definition": "house", "gender": "neuter"}'

    # Second call: cache hit, should NOT fetch from remote
    result2 = await service.get_or_fetch_details([word])

    assert len(result2) == 1
    assert result2[0].source_word == "huis"
    assert result2[0].payload == {"definition": "house", "gender": "neuter"}
    assert mock_remote.call_count == 1  # Should not increment

    await local_store.close()
