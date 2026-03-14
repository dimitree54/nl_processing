"""Test tiered exercise repeat-state transition matrix."""

import pytest

from nl_processing.database_cache._tiered_helpers import compute_next_repeat_state, validate_repeat_state_integrity


class TestTieredTransitionMatrix:
    """Test identical transition matrix as database package."""

    def test_wrong_answer_not_in_repeat_with_positive_scores_activates_repeat(self) -> None:
        """Wrong answer + not in repeat + has positive scores after update → activate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"ex1": 1, "ex2": 0},
            exercise_types=["ex1", "ex2"],
        )
        assert result is True

    def test_wrong_answer_not_in_repeat_with_no_positive_scores_stays_inactive(self) -> None:
        """Wrong answer + not in repeat + no positive scores after update → don't activate."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"ex1": 0, "ex2": 0},
            exercise_types=["ex1", "ex2"],
        )
        assert result is False

    def test_correct_answer_in_repeat_deactivates_repeat(self) -> None:
        """Correct answer + in repeat → deactivate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=1,
            scores_after_update={"ex1": 2, "ex2": 1},
            exercise_types=["ex1", "ex2"],
        )
        assert result is False

    def test_wrong_answer_in_repeat_with_positive_scores_keeps_repeat(self) -> None:
        """Wrong answer + in repeat + has positive score left → keep repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=-1,
            scores_after_update={"ex1": 0, "ex2": 1},
            exercise_types=["ex1", "ex2"],
        )
        assert result is True

    def test_wrong_answer_in_repeat_with_no_positive_scores_deactivates_repeat(self) -> None:
        """Wrong answer + in repeat + no positive score left → deactivate repeat."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=-1,
            scores_after_update={"ex1": 0, "ex2": 0},
            exercise_types=["ex1", "ex2"],
        )
        assert result is False

    def test_correct_answer_not_in_repeat_stays_inactive(self) -> None:
        """Correct answer + not in repeat → stay not in repeat (no-op)."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=1,
            scores_after_update={"ex1": 1, "ex2": 2},
            exercise_types=["ex1", "ex2"],
        )
        assert result is False

    def test_edge_case_single_exercise_type(self) -> None:
        """Test with single exercise type."""
        # Wrong answer, not in repeat, positive score after → activate
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"ex1": 1},
            exercise_types=["ex1"],
        )
        assert result is True

        # Wrong answer, not in repeat, zero score after → don't activate
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={"ex1": 0},
            exercise_types=["ex1"],
        )
        assert result is False

    def test_edge_case_missing_scores_default_to_zero(self) -> None:
        """Test that missing scores in scores_after_update default to 0."""
        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=-1,
            scores_after_update={},  # Empty scores dict
            exercise_types=["ex1", "ex2"],
        )
        assert result is False

    def test_edge_case_invalid_delta_preserves_state(self) -> None:
        """Test that invalid delta preserves current state."""
        result = compute_next_repeat_state(
            current_in_repeat=True,
            delta=0,  # Invalid delta
            scores_after_update={"ex1": 1},
            exercise_types=["ex1"],
        )
        assert result is True

        result = compute_next_repeat_state(
            current_in_repeat=False,
            delta=2,  # Invalid delta
            scores_after_update={"ex1": 1},
            exercise_types=["ex1"],
        )
        assert result is False


class TestTieredRepeatStateIntegrity:
    """Test repeat-state integrity validation."""

    def test_valid_repeat_state_with_positive_scores_passes(self) -> None:
        """Valid repeat-state (in_repeat=True with positive scores) should pass."""
        validate_repeat_state_integrity(
            in_repeat=True,
            scores={"ex1": 1, "ex2": 0},
            exercise_types=["ex1", "ex2"],
        )
        # Should not raise

    def test_valid_repeat_state_not_in_repeat_passes(self) -> None:
        """Valid repeat-state (in_repeat=False) should pass regardless of scores."""
        validate_repeat_state_integrity(
            in_repeat=False,
            scores={"ex1": 0, "ex2": 0},
            exercise_types=["ex1", "ex2"],
        )
        # Should not raise

    def test_invalid_repeat_state_raises_error(self) -> None:
        """Invalid repeat-state (in_repeat=True but no positive scores) should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repeat-state"):
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"ex1": 0, "ex2": 0},
                exercise_types=["ex1", "ex2"],
            )

    def test_invalid_repeat_state_missing_scores_raises_error(self) -> None:
        """Invalid repeat-state with missing scores should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid repeat-state"):
            validate_repeat_state_integrity(
                in_repeat=True,
                scores={"ex1": 0},  # Missing ex2
                exercise_types=["ex1", "ex2"],
            )
