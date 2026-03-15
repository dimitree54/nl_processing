"""Pure functions for tiered exercise repeat-state transitions and progress computation."""

from nl_processing.core.tiered_helpers import compute_next_repeat_state, validate_repeat_state_integrity
from nl_processing.core.tiered_models import TieredCandidate, TieredProgressSummary

# Re-export for backward compatibility
__all__ = ["compute_next_repeat_state", "validate_repeat_state_integrity", "compute_tiered_progress"]


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
