"""Pure functions for tiered exercise repeat-state transitions and progress computation."""

from nl_processing.database.tiered_models import TieredCandidate, TieredProgressSummary

__all__ = ["compute_next_repeat_state", "validate_repeat_state_integrity", "compute_tiered_progress"]


def compute_next_repeat_state(
    current_in_repeat: bool,
    delta: int,
    scores_after_update: dict[str, int],
    exercise_types: list[str],
) -> bool:
    """Compute next repeat-state from the tiered transition rules."""
    if delta not in {-1, 1}:
        return current_in_repeat
    if delta == 1:
        return False if current_in_repeat else current_in_repeat
    has_positive_score = any(scores_after_update.get(exercise_type, 0) > 0 for exercise_type in exercise_types)
    if current_in_repeat:
        return has_positive_score
    return has_positive_score


def validate_repeat_state_integrity(
    in_repeat: bool,
    scores: dict[str, int],
    exercise_types: list[str],
) -> None:
    """Reject persisted repeat-state rows that violate TBR-DB-6."""
    if not in_repeat:
        return
    if any(scores.get(exercise_type, 0) > 0 for exercise_type in exercise_types):
        return
    normalized_scores = {exercise_type: scores.get(exercise_type, 0) for exercise_type in exercise_types}
    msg = f"Invalid repeat-state: in_repeat=True requires a positive participating score, got {normalized_scores}"
    raise ValueError(msg)


def compute_tiered_progress(candidates: list[TieredCandidate], exercise_types: list[str]) -> TieredProgressSummary:
    """Compute tiered progress summary using all-positive completion rule TFR-DB-5.

    A word counts as "fully completed" only when ALL participating exercise scores are > 0.
    Missing scores default to 0.
    """
    total_words = len(candidates)
    if total_words == 0:
        return TieredProgressSummary(
            total_words=0,
            fully_completed_words=0,
            completion_ratio=0.0,
        )

    fully_completed_words = 0
    for candidate in candidates:
        # Check if ALL exercise types have positive scores
        all_positive = all(candidate.scores.get(et, 0) > 0 for et in exercise_types)
        if all_positive:
            fully_completed_words += 1

    completion_ratio = fully_completed_words / total_words

    return TieredProgressSummary(
        total_words=total_words,
        fully_completed_words=fully_completed_words,
        completion_ratio=completion_ratio,
    )
