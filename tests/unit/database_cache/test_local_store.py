"""Unit tests for LocalStore — SQLite data-access layer for the local cache."""

import pytest

from nl_processing.database_cache.local_store import LocalStore

_TABLES = {"cached_word_pairs", "cached_scores", "pending_score_events", "cache_metadata"}

_NOUN_PAIR = (1, "huis", "noun", 0, "dom", "noun")
_VERB_PAIR = (2, "lopen", "verb", 0, "begat", "verb")
_ADJ_PAIR = (3, "groot", "adjective", 0, "bolshoi", "adjective")


async def _insert_pairs(store: LocalStore, pairs: list[tuple[int, str, str, int, str, str]]) -> None:
    """Insert word pairs into the store via rebuild_snapshot."""
    await store.rebuild_snapshot(pairs, {})


@pytest.mark.asyncio
async def test_open_creates_tables(local_store: LocalStore) -> None:
    """Opening the store creates all required SQLite tables."""
    cur = await local_store._conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'",
    )
    rows = await cur.fetchall()
    table_names = {row[0] for row in rows}
    assert _TABLES.issubset(table_names)


@pytest.mark.asyncio
async def test_record_score_and_event(local_store: LocalStore) -> None:
    """Recording a score creates both a cached_scores row and a pending event."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-1")
    scores = await local_store._fetch_all("SELECT * FROM cached_scores")
    assert len(scores) == 1
    assert scores[0]["score"] == 1
    events = await local_store.get_pending_events()
    assert len(events) == 1
    assert events[0]["event_id"] == "evt-1"


@pytest.mark.asyncio
async def test_record_score_upserts(local_store: LocalStore) -> None:
    """Two score events for the same word+exercise accumulate the score."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-1")
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-2")
    scores = await local_store._fetch_all(
        "SELECT score FROM cached_scores WHERE source_word_id=1 AND exercise_type='flashcard'",
    )
    assert scores[0]["score"] == 2


@pytest.mark.asyncio
async def test_get_cached_word_pairs_filter(local_store: LocalStore) -> None:
    """Filtering by word_type returns only matching word pairs."""
    await _insert_pairs(local_store, [_NOUN_PAIR, _VERB_PAIR])
    nouns = await local_store.get_cached_word_pairs(word_type="noun")
    assert len(nouns) == 1
    assert nouns[0]["source_normalized_form"] == "huis"
    verbs = await local_store.get_cached_word_pairs(word_type="verb")
    assert len(verbs) == 1
    assert verbs[0]["source_normalized_form"] == "lopen"


@pytest.mark.asyncio
async def test_get_cached_word_pairs_limit(local_store: LocalStore) -> None:
    """Limit parameter restricts the number of returned word pairs."""
    await _insert_pairs(local_store, [_NOUN_PAIR, _VERB_PAIR, _ADJ_PAIR])
    result = await local_store.get_cached_word_pairs(limit=2)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_cached_word_pairs_with_scores_missing_default_zero(local_store: LocalStore) -> None:
    """Word pair without a score entry returns score=0."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    rows = await local_store.get_cached_word_pairs_with_scores(["flashcard"])
    assert len(rows) == 1
    assert rows[0]["score_flashcard"] == 0


@pytest.mark.asyncio
async def test_rebuild_snapshot_reapplies_pending(local_store: LocalStore) -> None:
    """Pending events are reapplied on top of new snapshot data."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-1")
    new_pairs = [_NOUN_PAIR, _VERB_PAIR]
    await local_store.rebuild_snapshot(new_pairs, {(1, "flashcard"): 5})
    scores = await local_store._fetch_all(
        "SELECT score FROM cached_scores WHERE source_word_id=1 AND exercise_type='flashcard'",
    )
    assert scores[0]["score"] == 6


@pytest.mark.asyncio
async def test_has_snapshot_empty(local_store: LocalStore) -> None:
    """has_snapshot returns False on an empty database."""
    result = await local_store.has_snapshot()
    assert result is False


@pytest.mark.asyncio
async def test_has_snapshot_with_data(local_store: LocalStore) -> None:
    """has_snapshot returns True after inserting word pairs."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    result = await local_store.has_snapshot()
    assert result is True


@pytest.mark.asyncio
async def test_mark_event_flushed(local_store: LocalStore) -> None:
    """Marking an event as flushed sets the flushed_at timestamp."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    await local_store.record_score_and_event(1, "flashcard", 1, "evt-1")
    await local_store.mark_event_flushed("evt-1")
    cur = await local_store._conn.execute(
        "SELECT flushed_at FROM pending_score_events WHERE event_id='evt-1'",
    )
    row = await cur.fetchone()
    assert row is not None
    assert row[0] is not None


@pytest.mark.asyncio
async def test_get_source_word_id(local_store: LocalStore) -> None:
    """Lookup returns the correct source_word_id or None for missing words."""
    await _insert_pairs(local_store, [_NOUN_PAIR])
    found = await local_store.get_source_word_id("huis", "noun")
    assert found == 1
    missing = await local_store.get_source_word_id("onbekend", "noun")
    assert missing is None
