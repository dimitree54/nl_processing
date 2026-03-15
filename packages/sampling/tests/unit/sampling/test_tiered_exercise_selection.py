"""Unit tests for TieredMultiExerciseSampler exercise-choice helper."""

from tests.unit.sampling.tiered_conftest import create_tiered_sampler, make_tiered_candidate


def test_repeat_mode_prefers_last_positive_exercise() -> None:
    """Negative tiered score enables repeat mode and selects the last positive exercise."""
    sampler = create_tiered_sampler(
        [],
        exercise_types=["flashcard", "fill_gap", "translation"],
        tiered_exercise_type="translation",
    )
    candidate = make_tiered_candidate(
        "huis",
        "dom",
        scores={"flashcard": 1, "fill_gap": 2, "translation": -1},
    )

    assert sampler._choose_exercise_for_word(candidate) == "fill_gap"


def test_repeat_mode_without_positive_scores_falls_back_to_first_exercise() -> None:
    """Repeat mode falls back to the first exercise when no positive scores exist."""
    sampler = create_tiered_sampler(
        [],
        exercise_types=["flashcard", "fill_gap"],
        tiered_exercise_type="fill_gap",
    )
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0, "fill_gap": -1})

    assert sampler._choose_exercise_for_word(candidate) == "flashcard"


def test_normal_mode_prefers_last_non_positive_exercise() -> None:
    """Normal mode selects the last exercise whose score is non-positive."""
    sampler = create_tiered_sampler([], exercise_types=["flashcard", "fill_gap", "translation"])
    candidate = make_tiered_candidate(
        "huis",
        "dom",
        scores={"flashcard": 1, "fill_gap": 0, "translation": 3},
    )

    assert sampler._choose_exercise_for_word(candidate) == "fill_gap"


def test_normal_mode_returns_last_when_all_scores_positive() -> None:
    """When every score is positive, the last exercise is returned."""
    sampler = create_tiered_sampler([], exercise_types=["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 1, "fill_gap": 2})

    assert sampler._choose_exercise_for_word(candidate) == "fill_gap"
