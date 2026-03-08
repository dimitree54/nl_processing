"""Unit tests for CacheSyncer — refresh and flush orchestration."""

import pytest

from nl_processing.database_cache.exceptions import CacheSyncError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.sync import CacheSyncer
from tests.unit.database_cache.conftest import MockProgressStore, make_scored_pair


async def _build_syncer(
    local_store: LocalStore,
    snapshot: list[object] | None = None,
) -> tuple[CacheSyncer, MockProgressStore]:
    """Create a CacheSyncer with mock remote pre-loaded with snapshot data."""
    await local_store.ensure_metadata(["flashcard"])
    mock_remote = MockProgressStore(
        snapshot=snapshot
        or [
            make_scored_pair("huis", "dom", 1, {"flashcard": 3}),
            make_scored_pair("boek", "kniga", 2, {"flashcard": 1}),
        ]
    )
    syncer = CacheSyncer(local_store, mock_remote)
    return syncer, mock_remote


@pytest.mark.asyncio
async def test_refresh_downloads_and_rebuilds(local_store: LocalStore) -> None:
    """After refresh, the local store contains the remote snapshot."""
    syncer, _remote = await _build_syncer(local_store)
    await syncer.refresh()
    pairs = await local_store.get_cached_word_pairs()
    assert len(pairs) == 2
    forms = {p["source_normalized_form"] for p in pairs}
    assert forms == {"huis", "boek"}


@pytest.mark.asyncio
async def test_refresh_updates_metadata(local_store: LocalStore) -> None:
    """Refresh sets last_refresh_completed_at in cache metadata."""
    syncer, _remote = await _build_syncer(local_store)
    await syncer.refresh()
    meta = await local_store.get_metadata()
    assert meta is not None
    assert meta["last_refresh_completed_at"] is not None


@pytest.mark.asyncio
async def test_flush_replays_events(local_store: LocalStore) -> None:
    """Flush sends pending local events to the remote store."""
    syncer, mock_remote = await _build_syncer(local_store)
    await syncer.refresh()
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-a")
    await local_store.record_score_and_event(2, "flashcard", -1, "evt-b")
    await syncer.flush()
    assert len(mock_remote.applied_deltas) == 2
    event_ids = {d["event_id"] for d in mock_remote.applied_deltas}
    assert event_ids == {"evt-a", "evt-b"}


@pytest.mark.asyncio
async def test_flush_marks_flushed(local_store: LocalStore) -> None:
    """Flushed events are no longer returned by get_pending_events."""
    syncer, _remote = await _build_syncer(local_store)
    await syncer.refresh()
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-c")
    await syncer.flush()
    pending = await local_store.get_pending_events()
    assert len(pending) == 0


@pytest.mark.asyncio
async def test_flush_handles_per_event_failure(local_store: LocalStore) -> None:
    """When one event fails, the other is still flushed successfully."""
    syncer, mock_remote = await _build_syncer(local_store)
    await syncer.refresh()
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-ok")
    await local_store.record_score_and_event(2, "flashcard", 1, "evt-fail")

    original_apply = mock_remote.apply_score_delta

    async def _failing_apply(
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None:
        if event_id == "evt-fail":
            raise RuntimeError("remote error")
        await original_apply(event_id, source_word_id, exercise_type, delta)

    mock_remote.apply_score_delta = _failing_apply  # type: ignore[assignment]
    await syncer.flush()
    assert len(mock_remote.applied_deltas) == 1
    assert mock_remote.applied_deltas[0]["event_id"] == "evt-ok"
    cur = await local_store._conn.execute(
        "SELECT last_error FROM pending_score_events WHERE event_id='evt-fail'",
    )
    row = await cur.fetchone()
    assert row is not None
    assert "remote error" in str(row[0])


@pytest.mark.asyncio
async def test_refresh_wraps_errors(local_store: LocalStore) -> None:
    """Remote failure during refresh raises CacheSyncError."""
    await local_store.ensure_metadata(["flashcard"])

    class FailingRemote:
        async def export_remote_snapshot(self) -> list[object]:
            raise ConnectionError("network down")

        async def apply_score_delta(
            self,
            event_id: str,
            source_word_id: int,
            exercise_type: str,
            delta: int,
        ) -> None:
            pass

    syncer = CacheSyncer(local_store, FailingRemote())
    with pytest.raises(CacheSyncError, match="network down"):
        await syncer.refresh()
