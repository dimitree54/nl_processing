"""Constructor tests for TieredMultiExerciseSampler."""

from tests.unit.sampling.tiered_conftest import create_tiered_sampler


def test_constructor_preserves_configuration() -> None:
    """Constructor stores the configured exercise metadata."""
    sampler = create_tiered_sampler(
        [],
        exercise_types=["flashcard", "fill_gap"],
        tiered_exercise_type="fill_gap",
        finished_exercise_weight=0.25,
    )

    assert sampler._exercise_types == ["flashcard", "fill_gap"]
    assert sampler._tiered_exercise_type == "fill_gap"
    assert sampler._finished_exercise_weight == 0.25


def test_constructor_allows_empty_exercise_types() -> None:
    """Constructor currently accepts an empty exercise list without validation."""
    sampler = create_tiered_sampler([], exercise_types=[])

    assert sampler._exercise_types == []
