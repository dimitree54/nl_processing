"""Unit tests for tiered exercise repeat-state transition matrix."""

import pytest

from nl_processing.database._tiered_helpers import (
    compute_next_repeat_state,
    validate_repeat_state_integrity,
)


class TestComputeNextRepeatState:
    """Test repeat-state transition rules TBR-DB-3..6."""

    def test_wrong_answer_not_in_repeat_has_positive_activates(self) -> None:
        """Wrong answer (delta=-1) + not in repeat + has positive → activate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"flashcard": 1, "typing": 0},
            exercise_types=["flashcard", "typing"],
        )
        assert result is True

    def test_wrong_answer_not_in_repeat_no_positive_dont_activate(self) -> None:
        """Wrong answer (delta=-1) + not in repeat + no positive → don't activate."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"flashcard": 0, "typing": -1},
            exercise_types=["flashcard", "typing"],
        )
        assert result is False

    def test_correct_answer_in_repeat_deactivates(self) -> None:
        """Correct answer (delta=+1) + in repeat → deactivate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=1,
            scores_after_update={"flashcard": 2, "typing": 1},
            exercise_types=["flashcard", "typing"],
        )
        assert result is False

    def test_wrong_answer_in_repeat_has_positive_keeps(self) -> None:
        """Wrong answer (delta=-1) + in repeat + has positive → keep repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=-1,
            scores_after_update={"flashcard": 0, "typing": 1},
            exercise_types=["flashcard", "typing"],
        )
        assert result is True

    def test_wrong_answer_in_repeat_no_positive_deactivates(self) -> None:
        """Wrong answer (delta=-1) + in repeat + no positive → deactivate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=-1,
            scores_after_update={"flashcard": 0, "typing": -2},
            exercise_types=["flashcard", "typing"],
        )
        assert result is False

    def test_correct_answer_not_in_repeat_stays_not_in_repeat(self) -> None:
        """Correct answer (delta=+1) + not in repeat → stay not in repeat (no-op)."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=1,
            scores_after_update={"flashcard": 3, "typing": 2},
            exercise_types=["flashcard", "typing"],
        )
        assert result is False

    def test_missing_scores_default_to_zero(self) -> None:
        """Missing scores in scores_after_update default to 0."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"flashcard": 1},  # typing missing
            exercise_types=["flashcard", "typing"],
        )
        assert result is True  # flashcard has positive score

    def test_invalid_delta_keeps_current_state(self) -> None:
        """Invalid delta values preserve current state."""
        # This shouldn't happen in practice due to validation, but test edge case
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=0,  # Invalid
            scores_after_update={"flashcard": 1},
            exercise_types=["flashcard"],
        )
        assert result is True  # Keeps current state

        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=2,  # Invalid
            scores_after_update={"flashcard": 1},
            exercise_types=["flashcard"],
        )
        assert result is False  # Keeps current state


class TestValidateRepeatStateIntegrity:
    """Test repeat-state integrity validation per TBR-DB-6."""

    def test_in_repeat_with_positive_score_valid(self) -> None:
        """in_repeat=True with positive score is valid."""
        # Should not raise
        validate_repeat_state_integrity(
            in_repeat=True,
            scores={"flashcard": 1, "typing": 0},
            exercise_types=["flashcard", "typing"],
        )

    def test_not_in_repeat_with_any_scores_valid(self) -> None:
        """in_repeat=False with any scores is valid."""
        # Should not raise
        validate_repeat_state_integrity(
            in_repeat=False,
            scores={"flashcard": 0, "typing": 0},
            exercise_types=["flashcard", "typing"],
        )

        validate_repeat_state_integrity(
            in_repeat=False,
            scores={"flashcard": 1, "typing": -1},
            exercise_types=["flashcard", "typing"],
        )

    def test_in_repeat_with_no_positive_scores_raises(self) -> None:
        """in_repeat=True with no positive scores raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repeat-state"):
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"flashcard": 0, "typing": -1},
                exercise_types=["flashcard", "typing"],
            )

    def test_in_repeat_with_all_zero_scores_raises(self) -> None:
        """in_repeat=True with all zero scores raises ValueError."""
        with pytest.raises(ValueError, match="Invalid repeat-state"):
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"flashcard": 0, "typing": 0},
                exercise_types=["flashcard", "typing"],
            )

    def test_in_repeat_with_missing_scores_treated_as_zero(self) -> None:
        """Missing scores are treated as 0 for validation."""
        with pytest.raises(ValueError, match="Invalid repeat-state"):
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"flashcard": 0},  # typing missing, treated as 0
                exercise_types=["flashcard", "typing"],
            )

    def test_error_message_includes_scores(self) -> None:
        """Error message includes score details for debugging."""
        with pytest.raises(ValueError) as exc_info:
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"flashcard": 0, "typing": -2},
                exercise_types=["flashcard", "typing"],
            )
        error_msg = str(exc_info.value)
        assert "flashcard" in error_msg
        assert "typing" in error_msg
        assert "0" in error_msg
        assert "-2" in error_msg
