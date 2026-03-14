"""Constructor validation tests for TieredExerciseSampler."""

from nl_processing.core.models import Language
import pytest

from nl_processing.sampling.tiered_sampler import TieredExerciseSampler
from tests.unit.sampling.tiered_conftest import MockTieredCandidateProvider


def test_empty_exercise_types_raises() -> None:
    """Empty exercise_types list raises ValueError."""
    with pytest.raises(ValueError, match="exercise_types must be a non-empty list"):
        TieredExerciseSampler(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            mode_slug="mixed",
            exercise_types=[],
        )


def test_finished_word_weight_zero_raises() -> None:
    """finished_word_weight=0 raises ValueError."""
    with pytest.raises(ValueError, match="finished_word_weight"):
        TieredExerciseSampler(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            mode_slug="mixed",
            exercise_types=["flashcard"],
            finished_word_weight=0,
        )


def test_finished_word_weight_negative_raises() -> None:
    """finished_word_weight=-0.5 raises ValueError."""
    with pytest.raises(ValueError, match="finished_word_weight"):
        TieredExerciseSampler(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            mode_slug="mixed",
            exercise_types=["flashcard"],
            finished_word_weight=-0.5,
        )


def test_finished_word_weight_one_valid() -> None:
    """finished_word_weight=1.0 is valid (boundary)."""
    mock_store = MockTieredCandidateProvider([])
    sampler = TieredExerciseSampler(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        mode_slug="mixed",
        exercise_types=["flashcard"],
        finished_word_weight=1.0,
        tiered_store=mock_store,
    )
    assert sampler._finished_word_weight == 1.0


def test_empty_mode_slug_raises() -> None:
    """Empty mode_slug raises ValueError."""
    with pytest.raises(ValueError, match="mode_slug must be non-empty"):
        TieredExerciseSampler(
            user_id="u1",
            source_language=Language.NL,
            target_language=Language.RU,
            mode_slug="",
            exercise_types=["flashcard"],
        )
