"""Integration tests for delete functionality."""

from datetime import timedelta
from pathlib import Path

from nl_processing.core.models import Language
import pytest
import pytest_asyncio

from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.service import DatabaseCacheService
from tests.integration.database_cache.conftest import MockProgressStore, make_scored_pair


# Add MockRemoteDelete here since it's easier than cross-importing
class MockRemoteDelete:
    """Fake remote delete port for testing."""

    def __init__(self) -> None:
        self.deleted_words: list[int] = []
        self.delete_error: Exception | None = None

    async def delete_word(self, source_word_id: int, exercise_types: list[str] | None = None) -> None:  # noqa: ARG002
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_words.append(source_word_id)

    async def delete_words(self, source_word_ids: list[int], exercise_types: list[str] | None = None) -> None:  # noqa: ARG002
        if self.delete_error is not None:
            raise self.delete_error
        self.deleted_words.extend(source_word_ids)


@pytest_asyncio.fixture
async def persistent_service(tmp_path: Path) -> tuple[DatabaseCacheService, Path]:
    """Service that can be closed and reopened to test persistence."""
    db_path = tmp_path / "persistent.db"
    mock_progress = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
            make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),
            make_scored_pair("auto", "mashina", 3, {"flashcard": 0}),
        ]
    )

    local_store = LocalStore(str(db_path))
    svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(tmp_path),
        remote_progress=mock_progress,
        remote_db=MockRemoteDelete(),
        local_store=local_store,
    )
    await svc.init()
    return svc, db_path


@pytest.mark.asyncio
async def test_delete_persists_across_close_reopen(persistent_service: tuple[DatabaseCacheService, Path]) -> None:
    """Delete a word, close/reopen SQLite, verify word is still gone."""
    svc, db_path = persistent_service

    # Verify 3 words initially
    words_before = await svc.get_words()
    assert len(words_before) == 3

    # Delete word 2
    await svc.delete_word(2)

    # Verify only 2 words remain
    words_after_delete = await svc.get_words()
    assert len(words_after_delete) == 2
    remaining_ids = [w.source_word_id for w in await svc.get_word_pairs_with_scores()]
    assert 2 not in remaining_ids
    assert 1 in remaining_ids
    assert 3 in remaining_ids

    # Close the service
    await svc._local.close()  # type: ignore[union-attr]

    # Reopen with new service instance - simulate that the remote also doesn't have the deleted word
    new_local_store = LocalStore(str(db_path))
    new_mock_progress = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
            make_scored_pair("auto", "mashina", 3, {"flashcard": 0}),
            # word 2 is missing - simulating it was deleted remotely too
        ]
    )
    new_svc = DatabaseCacheService(
        user_id="test_user",
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        cache_ttl=timedelta(minutes=30),
        cache_dir=str(db_path.parent),
        remote_progress=new_mock_progress,
        remote_db=MockRemoteDelete(),
        local_store=new_local_store,
    )
    await new_svc.init()

    # Word should still be gone
    words_after_reopen = await new_svc.get_words()
    assert len(words_after_reopen) == 2
    final_ids = [w.source_word_id for w in await new_svc.get_word_pairs_with_scores()]
    assert 2 not in final_ids
    assert 1 in final_ids
    assert 3 in final_ids

    await new_svc._local.close()  # type: ignore[union-attr]


@pytest.mark.asyncio
async def test_delete_and_refresh_does_not_bring_word_back(
    persistent_service: tuple[DatabaseCacheService, Path],
) -> None:
    """Delete word from remote mock, update mock to not include word, refresh, word still gone."""
    svc, _db_path = persistent_service

    # Get the mock progress store and remove word 2 from its snapshot
    mock_progress = svc._remote_progress  # type: ignore[attr-defined]
    assert isinstance(mock_progress, MockProgressStore)

    # Remove word 2 from the mock snapshot (simulating it was deleted remotely)
    mock_progress.snapshot = [
        make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
        make_scored_pair("auto", "mashina", 3, {"flashcard": 0}),
    ]

    # Verify 3 words initially in cache
    words_before = await svc.get_words()
    assert len(words_before) == 3

    # Delete word 2 (which succeeds because remote mock allows it)
    await svc.delete_word(2)

    # Verify word is gone from cache
    words_after_delete = await svc.get_words()
    assert len(words_after_delete) == 2

    # Refresh cache (should sync with remote snapshot that doesn't include word 2)
    await svc.refresh()

    # Word 2 should still be gone (not brought back by refresh)
    words_after_refresh = await svc.get_words()
    assert len(words_after_refresh) == 2
    final_ids = [w.source_word_id for w in await svc.get_word_pairs_with_scores()]
    assert 2 not in final_ids
    assert 1 in final_ids
    assert 3 in final_ids

    await svc._local.close()  # type: ignore[union-attr]
