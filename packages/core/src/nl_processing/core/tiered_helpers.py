"""Pure functions for tiered exercise repeat-state transitions."""


def compute_next_repeat_state(
    current_in_repeat: bool,
    delta: int,
    scores_after_update: dict[str, int],
    exercise_types: list[str],
) -> bool:
    """Compute next repeat-state based on transition rules TBR-DB-3..6.

    Args:
        current_in_repeat: Current repeat mode state
        delta: Score delta applied (+1 or -1)
        scores_after_update: All exercise scores after the delta was applied
        exercise_types: List of participating exercise types

    Returns:
        New repeat-state value

    Transition rules:
    - Wrong answer (delta=-1) + not in repeat + has at least one positive score after update -> activate repeat
    - Wrong answer (delta=-1) + not in repeat + no positive score after update -> don't activate
    - Correct answer (delta=+1) + in repeat -> deactivate repeat
    - Wrong answer (delta=-1) + in repeat + has positive score left -> keep repeat
    - Wrong answer (delta=-1) + in repeat + no positive score left -> deactivate repeat
    - Correct answer (delta=+1) + not in repeat -> stay not in repeat (no-op)
    """
    has_positive_score = any(scores_after_update.get(et, 0) > 0 for et in exercise_types)

    if delta == -1:  # Wrong answer
        if not current_in_repeat:
            # Activate repeat only if there's at least one positive score after update
            return has_positive_score
        else:
            # Keep repeat if there's still positive score left, otherwise deactivate
            return has_positive_score
    elif delta == 1:  # Correct answer
        if current_in_repeat:
            # Deactivate repeat
            return False
        else:
            # Stay not in repeat (no-op)
            return False
    else:
        # Should never happen due to validation, but keep current state
        return current_in_repeat


def validate_repeat_state_integrity(in_repeat: bool, scores: dict[str, int], exercise_types: list[str]) -> None:
    """Validate repeat-state integrity per TBR-DB-6.

    Raises ValueError if in_repeat=True but no participating score is positive.
    """
    if in_repeat:
        has_positive_score = any(scores.get(et, 0) > 0 for et in exercise_types)
        if not has_positive_score:
            positive_scores = {et: scores.get(et, 0) for et in exercise_types if scores.get(et, 0) > 0}
            msg = (
                f"Invalid repeat-state: in_repeat=True but no positive scores found. "
                f"Scores: {scores}, positive: {positive_scores}"
            )
            raise ValueError(msg)
