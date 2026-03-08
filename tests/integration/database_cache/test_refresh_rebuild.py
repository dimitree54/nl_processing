"""Integration tests — refresh / rebuild behaviour with file-based SQLite and mocked remote."""

import json
from pathlib import Path

import pytest

from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.sync import CacheSyncer
from tests.integration.database_cache.conftest import MockProgressStore, make_scored_pair


async def _open_store_with_metadata(db_path: Path, exercise_types: list[str]) -> LocalStore:
    """Open a file-backed LocalStore and initialise metadata."""
    store = LocalStore(str(db_path))
    await store.open()
    await store.ensure_metadata(exercise_types)
    return store


@pytest.mark.asyncio
async def test_refresh_replaces_snapshot_atomically(db_path: Path) -> None:
    """A second refresh entirely replaces the previous snapshot."""
    initial = [
        make_scored_pair("huis", "dom", 1, {"flashcard": 0}),
        make_scored_pair("boek", "kniga", 2, {"flashcard": 0}),
        make_scored_pair("kat", "koshka", 3, {"flashcard": 0}),
        make_scored_pair("hond", "sobaka", 4, {"flashcard": 0}),
        make_scored_pair("vis", "ryba", 5, {"flashcard": 0}),
    ]
    store = await _open_store_with_metadata(db_path, ["flashcard"])
    remote = MockProgressStore(snapshot=initial)
    syncer = CacheSyncer(store, remote)
    await syncer.refresh()
    pairs_before = await store.get_cached_word_pairs()
    assert len(pairs_before) == 5

    replacement = [
        make_scored_pair("tafel", "stol", 10, {"flashcard": 2}),
        make_scored_pair("stoel", "stul", 11, {"flashcard": 1}),
        make_scored_pair("deur", "dver", 12, {"flashcard": 0}),
    ]
    remote.snapshot = replacement
    await syncer.refresh()

    pairs_after = await store.get_cached_word_pairs()
    assert len(pairs_after) == 3
    forms = {p["source_normalized_form"] for p in pairs_after}
    assert forms == {"tafel", "stoel", "deur"}
    await store.close()


@pytest.mark.asyncio
async def test_refresh_preserves_pending_events(db_path: Path) -> None:
    """Pending events survive a refresh and their deltas are re-applied on top of new remote scores."""
    initial = [
        make_scored_pair("huis", "dom", 1, {"flashcard": 5}),
        make_scored_pair("boek", "kniga", 2, {"flashcard": 3}),
    ]
    store = await _open_store_with_metadata(db_path, ["flashcard"])
    remote = MockProgressStore(snapshot=initial)
    syncer = CacheSyncer(store, remote)
    await syncer.refresh()

    await store.record_score_and_event(1, "flashcard", 1, "evt-local-1")
    await store.record_score_and_event(1, "flashcard", 1, "evt-local-2")

    updated_remote = [
        make_scored_pair("huis", "dom", 1, {"flashcard": 10}),
        make_scored_pair("boek", "kniga", 2, {"flashcard": 3}),
    ]
    remote.snapshot = updated_remote
    await syncer.refresh()

    events = await store.get_pending_events()
    assert len(events) == 2

    scored = await store.get_cached_word_pairs_with_scores(["flashcard"])
    huis_row = [r for r in scored if r["source_normalized_form"] == "huis"][0]
    assert int(huis_row["score_flashcard"]) == 12
    await store.close()


@pytest.mark.asyncio
async def test_changed_exercise_types_triggers_metadata_update(db_path: Path) -> None:
    """Calling ensure_metadata with a new exercise_types list updates the stored metadata."""
    store = await _open_store_with_metadata(db_path, ["flashcard"])
    meta = await store.get_metadata()
    assert meta is not None
    assert json.loads(str(meta["exercise_types"])) == ["flashcard"]

    await store.ensure_metadata(["flashcard", "multiple_choice"])

    meta2 = await store.get_metadata()
    assert meta2 is not None
    assert json.loads(str(meta2["exercise_types"])) == ["flashcard", "multiple_choice"]
    await store.close()


@pytest.mark.asyncio
async def test_refresh_with_zero_word_pairs(db_path: Path) -> None:
    """Remote returning an empty snapshot results in an empty cache without errors."""
    store = await _open_store_with_metadata(db_path, ["flashcard"])
    remote = MockProgressStore(snapshot=[])
    syncer = CacheSyncer(store, remote)
    await syncer.refresh()

    pairs = await store.get_cached_word_pairs()
    assert len(pairs) == 0
    assert await store.has_snapshot() is False
    meta = await store.get_metadata()
    assert meta is not None
    assert meta["last_refresh_completed_at"] is not None
    await store.close()
