"""Integration tests — SQLite file persistence across close / reopen cycles."""

import json
from pathlib import Path

import pytest

from nl_processing.database_cache.local_store import LocalStore

_PAIR_HUIS = (1, "huis", "noun", 0, "dom", "noun")
_PAIR_BOEK = (2, "boek", "noun", 0, "kniga", "noun")


@pytest.mark.asyncio
async def test_sqlite_file_persists_across_close_reopen(db_path: Path) -> None:
    """Data written via rebuild_snapshot survives close + reopen of the same file."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.rebuild_snapshot([_PAIR_HUIS, _PAIR_BOEK], {})
    await store.close()

    store2 = LocalStore(str(db_path))
    await store2.open()
    pairs = await store2.get_cached_word_pairs()
    assert len(pairs) == 2
    forms = {p["source_normalized_form"] for p in pairs}
    assert forms == {"huis", "boek"}
    await store2.close()


@pytest.mark.asyncio
async def test_pending_events_survive_restart(db_path: Path) -> None:
    """Pending score events recorded before close are available after reopen."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.rebuild_snapshot([_PAIR_HUIS, _PAIR_BOEK], {})
    await store.record_score_and_event(1, "flashcard", 1, "evt-1")
    await store.record_score_and_event(2, "flashcard", -1, "evt-2")
    await store.record_score_and_event(1, "flashcard", 1, "evt-3")
    await store.close()

    store2 = LocalStore(str(db_path))
    await store2.open()
    events = await store2.get_pending_events()
    assert len(events) == 3
    ids = {str(e["event_id"]) for e in events}
    assert ids == {"evt-1", "evt-2", "evt-3"}
    await store2.close()


@pytest.mark.asyncio
async def test_cache_metadata_survives_restart(db_path: Path) -> None:
    """Metadata written via ensure_metadata + update_metadata is intact after reopen."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.ensure_metadata(["flashcard"])
    await store.update_metadata(last_refresh_completed_at="2025-01-01T00:00:00+00:00")
    await store.close()

    store2 = LocalStore(str(db_path))
    await store2.open()
    meta = await store2.get_metadata()
    assert meta is not None
    assert json.loads(str(meta["exercise_types"])) == ["flashcard"]
    assert meta["last_refresh_completed_at"] == "2025-01-01T00:00:00+00:00"
    await store2.close()


@pytest.mark.asyncio
async def test_deleted_file_recreates_schema_on_open(db_path: Path) -> None:
    """If the SQLite file is deleted between close and reopen, open() recreates the schema."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.rebuild_snapshot([_PAIR_HUIS], {})
    await store.close()

    db_path.unlink()
    assert not db_path.exists()

    store2 = LocalStore(str(db_path))
    await store2.open()
    pairs = await store2.get_cached_word_pairs()
    assert len(pairs) == 0
    assert await store2.has_snapshot() is False
    await store2.close()
