"""Integration tests — flush retry behaviour with file-based SQLite and mocked remote."""

from pathlib import Path

import pytest

from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.sync import CacheSyncer
from tests.integration.database_cache.conftest import MockProgressStore, make_scored_pair


async def _setup_store_with_snapshot(
    db_path: Path,
    mock: MockProgressStore,
) -> tuple[LocalStore, CacheSyncer]:
    """Open a file-backed store, initialise metadata, and refresh from the mock."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.ensure_metadata(["flashcard"])
    syncer = CacheSyncer(store, mock)
    await syncer.refresh()
    return store, syncer


@pytest.mark.asyncio
async def test_successful_flush_marks_events_flushed(db_path: Path) -> None:
    """After a successful flush, get_pending_events returns nothing."""
    remote = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
        ]
    )
    store, syncer = await _setup_store_with_snapshot(db_path, remote)
    await store.record_score_and_event(1, "flashcard", 1, "evt-a")
    await store.record_score_and_event(1, "flashcard", 1, "evt-b")

    await syncer.flush()

    pending = await store.get_pending_events()
    assert len(pending) == 0
    assert len(remote.applied_deltas) == 2
    await store.close()


@pytest.mark.asyncio
async def test_failed_flush_keeps_events_pending(db_path: Path) -> None:
    """When apply_score_delta raises, events stay pending with last_error set."""
    remote = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
        ]
    )
    store, syncer = await _setup_store_with_snapshot(db_path, remote)
    await store.record_score_and_event(1, "flashcard", 1, "evt-fail-1")
    await store.record_score_and_event(1, "flashcard", 1, "evt-fail-2")

    remote.apply_error = ConnectionError("network unreachable")
    await syncer.flush()

    pending = await store.get_pending_events()
    assert len(pending) == 2
    for evt in pending:
        assert evt["last_error"] is not None
        assert "network unreachable" in str(evt["last_error"])
    assert len(remote.applied_deltas) == 0
    await store.close()


@pytest.mark.asyncio
async def test_repeated_flush_is_idempotent(db_path: Path) -> None:
    """Flushing twice does not send already-flushed events a second time."""
    remote = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
        ]
    )
    store, syncer = await _setup_store_with_snapshot(db_path, remote)
    await store.record_score_and_event(1, "flashcard", 1, "evt-once")

    await syncer.flush()
    assert len(remote.applied_deltas) == 1

    await syncer.flush()
    assert len(remote.applied_deltas) == 1
    await store.close()


@pytest.mark.asyncio
async def test_mixed_success_failure_during_flush(db_path: Path) -> None:
    """First and third events flush; second event fails and retains its error."""
    remote = MockProgressStore(
        snapshot=[
            make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
            make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),
            make_scored_pair("kat", "koshka", 3, {"flashcard": 0}),
        ]
    )
    store, syncer = await _setup_store_with_snapshot(db_path, remote)

    await store.record_score_and_event(1, "flashcard", 1, "evt-ok-1")
    await store.record_score_and_event(2, "flashcard", 1, "evt-fail")
    await store.record_score_and_event(3, "flashcard", 1, "evt-ok-2")

    remote.apply_errors_by_call = [None, RuntimeError("transient"), None]
    await syncer.flush()

    flushed_ids = {str(d["event_id"]) for d in remote.applied_deltas}
    assert flushed_ids == {"evt-ok-1", "evt-ok-2"}

    pending = await store.get_pending_events()
    assert len(pending) == 1
    assert str(pending[0]["event_id"]) == "evt-fail"
    assert "transient" in str(pending[0]["last_error"])
    await store.close()
