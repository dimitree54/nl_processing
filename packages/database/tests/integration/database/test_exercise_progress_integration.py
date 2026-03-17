"""Integration tests for ExerciseProgressStore basic operations against real Neon."""

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database_core.backend.neon import NeonBackend
import pytest

from nl_processing.database.exercise_progress import ExerciseProgressStore
from tests.integration.database.conftest import (
    make_seeded_word_set,
    make_unique_user_id,
)


@pytest.mark.asyncio
async def test_increment_score_updates(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """increment() updates scores in real database."""
    user_id = make_unique_user_id()

    # Seed translated words
    word_specs = [
        ("huis", "house", PartOfSpeech.NOUN),
        ("auto", "car", PartOfSpeech.NOUN),
    ]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )

    # Increment scores
    await store.increment(pairs[0].source_word_id, "flashcard", 1)
    await store.increment(pairs[0].source_word_id, "flashcard", 1)  # total: 2
    await store.increment(pairs[1].source_word_id, "flashcard", -1)

    # Verify scores
    scored = await store.get_word_pairs_with_scores()
    scores_by_form = {sp.pair.source.normalized_form: sp.scores["flashcard"] for sp in scored}

    assert scores_by_form["huis"] == 2
    assert scores_by_form["auto"] == -1


@pytest.mark.asyncio
async def test_default_zero_scores(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """Words without explicit scores default to zero."""
    user_id = make_unique_user_id()

    # Seed translated words
    word_specs = [
        ("word1", "target1", PartOfSpeech.NOUN),
        ("word2", "target2", PartOfSpeech.NOUN),
    ]
    await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    store = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )

    # Get scores without any increments
    scored = await store.get_word_pairs_with_scores()
    assert len(scored) == 2

    for sp in scored:
        assert sp.scores["flashcard"] == 0


@pytest.mark.asyncio
async def test_cross_instance_persistence(
    neon_backend: NeonBackend,
    make_seeded_word_set: make_seeded_word_set,
) -> None:
    """Scores persist across different store instances."""
    user_id = make_unique_user_id()

    # Seed word
    word_specs = [("persistent", "persistent_target", PartOfSpeech.NOUN)]
    pairs = await make_seeded_word_set(word_specs=word_specs, user_id=user_id)

    # Store 1: set score by incrementing multiple times
    store1 = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )
    source_word_id = pairs[0].source_word_id
    await store1.increment(source_word_id, "flashcard", 1)
    await store1.increment(source_word_id, "flashcard", 1)
    await store1.increment(source_word_id, "flashcard", 1)

    # Store 2: read score
    store2 = ExerciseProgressStore(
        user_id=user_id,
        source_language=Language.NL,
        target_language=Language.RU,
        exercise_types=["flashcard"],
        backend=neon_backend,
    )
    scored = await store2.get_word_pairs_with_scores()
    assert len(scored) == 1
    assert scored[0].scores["flashcard"] == 3
