"""Integration test for detailed cache schema invalidation."""

from pathlib import Path

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.database_cache._detailed_local_store import DetailedLocalStore
from nl_processing.database_cache.detailed_cache import DetailedWordCacheService
from tests.integration.database_cache.conftest import make_remote_record
from tests.integration.database_cache.integration_mocks import MockRemoteDetailedWordStore, MockSchemaChecker


@pytest.mark.asyncio
async def test_schema_invalidation_with_real_deletion(tmp_path: Path) -> None:
    """Test schema invalidation with real SQLite deletion and re-fetch."""
    # Create real SQLite file
    db_path = tmp_path / "test_schema_invalidation.db"
    local_store = DetailedLocalStore(str(db_path))
    await local_store.open()

    # Pre-populate cache with "old" schema version
    await local_store.upsert_cached_detail("boek", "noun", "nl_ru_noun", 1, '{"definition": "old_book"}')

    # Verify it's there
    cached_before = await local_store.get_cached_detail("boek", "noun")
    assert cached_before is not None
    assert cached_before["schema_version"] == 1

    # Create schema checker that marks version 1 as incompatible
    schema_checker = MockSchemaChecker({"nl_ru_noun": [1]})  # Version 1 is incompatible

    # Create mock remote with updated record
    remote_record = make_remote_record(
        "boek", {"definition": "new_book", "gender": "neuter"}, schema_version=2
    )
    mock_remote = MockRemoteDetailedWordStore([remote_record])

    service = DetailedWordCacheService(
        Language.NL, Language.RU, remote_store=mock_remote, local_store=local_store, schema_checker=schema_checker
    )

    word = Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL)
    result = await service.get_or_fetch_details([word])

    assert len(result) == 1
    assert result[0].source_word == "boek"
    assert result[0].payload == {"definition": "new_book", "gender": "neuter"}
    assert result[0].schema_version == 2

    # Verify old record was deleted and new one persisted
    cached_after = await local_store.get_cached_detail("boek", "noun")
    assert cached_after is not None
    assert cached_after["schema_version"] == 2
    assert cached_after["payload"] == '{"definition": "new_book", "gender": "neuter"}'

    # Verify remote was called for re-fetch
    assert mock_remote.call_count == 1

    await local_store.close()
