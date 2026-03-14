"""Unit tests for TieredExerciseSampler exercise selection logic."""

from nl_processing.core.models import Language
import pytest

from nl_processing.sampling.tiered_sampler import TieredExerciseSampler
from tests.unit.sampling.tiered_conftest import MockTieredCandidateProvider, make_tiered_candidate


def create_sampler(exercise_types: list[str]) -> TieredExerciseSampler:
    """Create a TieredExerciseSampler with given exercise types."""
    mock_store = MockTieredCandidateProvider([])
    return TieredExerciseSampler(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        mode_slug="mixed",
        exercise_types=exercise_types,
        tiered_store=mock_store,  # Use mock store to avoid DATABASE_URL requirement
    )


# ---- normal mode exercise selection ----


def test_normal_mode_both_exercises_zero_score() -> None:
    """Normal mode with scores {"flashcard": 0, "fill_gap": 0} selects fill_gap (most complex)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0, "fill_gap": 0})

    selected = sampler._select_exercise(candidate)
    assert selected == "fill_gap"


def test_normal_mode_flashcard_positive_fill_gap_zero() -> None:
    """Normal mode with scores {"flashcard": 2, "fill_gap": 0} selects fill_gap (only non-positive)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 2, "fill_gap": 0})

    selected = sampler._select_exercise(candidate)
    assert selected == "fill_gap"


def test_normal_mode_flashcard_zero_fill_gap_positive() -> None:
    """Normal mode with scores {"flashcard": 0, "fill_gap": 3} selects flashcard (most complex non-positive)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0, "fill_gap": 3})

    selected = sampler._select_exercise(candidate)
    assert selected == "flashcard"


# ---- repeat mode exercise selection ----


def test_repeat_mode_flashcard_positive_fill_gap_negative() -> None:
    """Repeat mode with scores {"flashcard": 2, "fill_gap": -1} selects flashcard (most complex positive)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 2, "fill_gap": -1}, in_repeat_mode=True)

    selected = sampler._select_exercise(candidate)
    assert selected == "flashcard"


def test_repeat_mode_both_positive() -> None:
    """Repeat mode with scores {"flashcard": 1, "fill_gap": 3} selects fill_gap (most complex positive)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 1, "fill_gap": 3}, in_repeat_mode=True)

    selected = sampler._select_exercise(candidate)
    assert selected == "fill_gap"


# ---- fully finished review ----


def test_fully_finished_review_selects_most_complex() -> None:
    """Normal mode with all positive scores selects the most complex exercise (last in list)."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 2, "fill_gap": 3})

    selected = sampler._select_exercise(candidate)
    assert selected == "fill_gap"


# ---- invalid repeat state ----


def test_invalid_repeat_state_raises() -> None:
    """Repeat mode with all non-positive scores raises ValueError."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0, "fill_gap": -1}, in_repeat_mode=True)

    with pytest.raises(ValueError, match="Invalid repeat state"):
        sampler._select_exercise(candidate)


def test_invalid_repeat_state_no_scores_raises() -> None:
    """Repeat mode with no scores raises ValueError."""
    sampler = create_sampler(["flashcard", "fill_gap"])
    candidate = make_tiered_candidate("huis", "dom", scores={}, in_repeat_mode=True)

    with pytest.raises(ValueError, match="Invalid repeat state"):
        sampler._select_exercise(candidate)


# ---- three-exercise tier tests ----


def test_three_tier_normal_mode_complex_selection() -> None:
    """Three exercises: normal mode selects most complex non-positive."""
    sampler = create_sampler(["flashcard", "fill_gap", "translation"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 2, "fill_gap": 0, "translation": 0})

    selected = sampler._select_exercise(candidate)
    assert selected == "translation"  # Most complex among non-positive (fill_gap, translation)


def test_three_tier_repeat_mode_complex_selection() -> None:
    """Three exercises: repeat mode selects most complex positive."""
    sampler = create_sampler(["flashcard", "fill_gap", "translation"])
    candidate = make_tiered_candidate(
        "huis", "dom", scores={"flashcard": 1, "fill_gap": 0, "translation": 3}, in_repeat_mode=True
    )

    selected = sampler._select_exercise(candidate)
    assert selected == "translation"  # Most complex among positive (flashcard, translation)


def test_three_tier_fully_finished_review() -> None:
    """Three exercises: fully finished review selects most complex (last in list)."""
    sampler = create_sampler(["flashcard", "fill_gap", "translation"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 1, "fill_gap": 2, "translation": 3})

    selected = sampler._select_exercise(candidate)
    assert selected == "translation"


def test_three_tier_normal_mode_only_first_zero() -> None:
    """Three exercises: normal mode with only first exercise at zero selects first."""
    sampler = create_sampler(["flashcard", "fill_gap", "translation"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0, "fill_gap": 2, "translation": 3})

    selected = sampler._select_exercise(candidate)
    assert selected == "flashcard"  # Only non-positive exercise


# ---- single exercise edge cases ----


def test_single_exercise_normal_mode() -> None:
    """Single exercise: normal mode always returns that exercise."""
    sampler = create_sampler(["flashcard"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0})

    selected = sampler._select_exercise(candidate)
    assert selected == "flashcard"


def test_single_exercise_repeat_mode_positive() -> None:
    """Single exercise: repeat mode with positive score returns that exercise."""
    sampler = create_sampler(["flashcard"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 2}, in_repeat_mode=True)

    selected = sampler._select_exercise(candidate)
    assert selected == "flashcard"


def test_single_exercise_repeat_mode_invalid() -> None:
    """Single exercise: repeat mode with non-positive score raises ValueError."""
    sampler = create_sampler(["flashcard"])
    candidate = make_tiered_candidate("huis", "dom", scores={"flashcard": 0}, in_repeat_mode=True)

    with pytest.raises(ValueError, match="Invalid repeat state"):
        sampler._select_exercise(candidate)
