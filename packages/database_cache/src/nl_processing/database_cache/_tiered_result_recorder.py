"""Helper for recording tiered exercise results."""

import asyncio
from uuid import uuid4

from nl_processing.database_cache._tiered_cache_helpers import background_tiered_flush
from nl_processing.database_cache._tiered_helpers import compute_next_repeat_state
from nl_processing.database_cache._tiered_local_store import TieredLocalStore
from nl_processing.database_cache.tiered_sync import TieredCacheSyncer


async def record_tiered_result_impl(
    local_store: TieredLocalStore,
    syncer: TieredCacheSyncer,
    mode_slug: str,
    exercise_types: list[str],
    source_word_id: int,
    exercise_type: str,
    delta: int,
) -> None:
    """Implementation logic for recording tiered results."""
    # Get current state for this word
    rows = await local_store.get_tiered_candidates(mode_slug, exercise_types)
    word_row = None
    for row in rows:
        if int(row["source_word_id"]) == source_word_id:
            word_row = row
            break

    if word_row is None:
        msg = f"Word with source_word_id {source_word_id} not found in cache"
        raise ValueError(msg)

    # Compute current scores and next state
    current_in_repeat = bool(word_row["in_repeat_mode"])
    current_scores = {et: int(word_row.get(f"score_{et}", 0)) for et in exercise_types}

    # Compute scores after update
    scores_after_update = current_scores.copy()
    scores_after_update[exercise_type] = max(0, current_scores[exercise_type] + delta)

    # Compute next repeat state
    next_in_repeat = compute_next_repeat_state(current_in_repeat, delta, scores_after_update, exercise_types)

    # Record atomically
    event_id = str(uuid4())
    await local_store.record_tiered_score_and_event(
        mode_slug, source_word_id, exercise_type, delta, event_id, next_in_repeat
    )

    # Trigger background flush
    asyncio.create_task(background_tiered_flush(syncer))
