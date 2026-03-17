"""Integration tests for ExerciseProgressStore snapshots and replay against real Neon."""

import uuid

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.integration.database.conftest import (
    make_seeded_word_set,
    make_unique_user_id,
    seed_word_scores,
)


@pytest.mark.asyncio
async def test_export_remote_snapshot(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
    seed_word_scores: seed_word_scores,
) -> None:
    """export_remote_snapshot returns canonical WordPairSnapshot records."""
    user_id = make_unique_user_id()

    # Seed words with scores
    word_specs = [
        ("export1", "export1_target", PartOfSpeech.NOUN),
        ("export2", "export2_target", PartOfSpeech.VERB),
    ]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Set scores
    await seed_word_scores(pairs[0].source_word_id, user_id, {"flashcard": 4})
    await seed_word_scores(pairs[1].source_word_id, user_id, {"flashcard": -2})

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )

    # Export snapshot
    snapshot = await store.export_remote_snapshot()
    assert len(snapshot) == 2

    # Verify snapshot structure
    snapshot_by_form = {entry.pair.source.normalized_form: entry for entry in snapshot}

    entry1 = snapshot_by_form["export1"]
    assert entry1.source_word_id == pairs[0].source_word_id
    assert entry1.target_word_id == pairs[0].target_word_id
    assert entry1.scores["flashcard"] == 4
    assert entry1.added_at is not None

    entry2 = snapshot_by_form["export2"]
    assert entry2.source_word_id == pairs[1].source_word_id
    assert entry2.target_word_id == pairs[1].target_word_id
    assert entry2.scores["flashcard"] == -2
    assert entry2.added_at is not None


@pytest.mark.asyncio
async def test_apply_score_delta_idempotent_replay(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """apply_score_delta with event IDs supports idempotent replay."""
    user_id = make_unique_user_id()

    # Seed word
    word_specs = [("replay", "replay_target", PartOfSpeech.NOUN)]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )

    event_id = f"test_event_{uuid.uuid4().hex}"
    source_word_id = pairs[0].source_word_id

    # First application
    await store.apply_score_delta(
        event_id=event_id,
        source_word_id=source_word_id,
        exercise_type="flashcard",
        delta=1,
    )

    # Verify score is applied
    scored = await store.get_word_pairs_with_scores()
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 1

    # Second application with same event_id (replay)
    await store.apply_score_delta(
        event_id=event_id,
        source_word_id=source_word_id,
        exercise_type="flashcard",
        delta=1,
    )

    # Score should not change (idempotent)
    scored_after_replay = await store.get_word_pairs_with_scores()
    assert scored_after_replay[0].scores["flashcard"] == 1

    # Different event_id should apply
    different_event_id = f"different_event_{uuid.uuid4().hex}"
    await store.apply_score_delta(
        event_id=different_event_id,
        source_word_id=source_word_id,
        exercise_type="flashcard",
        delta=1,
    )

    scored_after_new_event = await store.get_word_pairs_with_scores()
    assert scored_after_new_event[0].scores["flashcard"] == 2


@pytest.mark.asyncio
async def test_multiple_exercise_types(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """Store handles multiple exercise types independently."""
    user_id = make_unique_user_id()

    # Seed word
    word_specs = [("multi", "multi_target", PartOfSpeech.NOUN)]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard", "typing"],
        backend=neon_backend,
    )

    source_word_id = pairs[0].source_word_id

    # Set different scores for different exercise types
    await store.increment(source_word_id, "flashcard", 1)
    await store.increment(source_word_id, "flashcard", 1)
    await store.increment(source_word_id, "typing", -1)

    # Verify both scores
    scored = await store.get_word_pairs_with_scores()
    assert len(scored) == 1
    scores = scored[0].scores
    assert scores["flashcard"] == 2
    assert scores["typing"] == -1
