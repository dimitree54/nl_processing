"""Pure functions for tiered exercise repeat-state transitions and progress computation."""

from nl_processing.core.tiered_helpers import compute_next_repeat_state, validate_repeat_state_integrity
from nl_processing.core.tiered_models import TieredProgressSummary

# Re-export for backward compatibility
__all__ = ["compute_next_repeat_state", "validate_repeat_state_integrity", "compute_local_tiered_progress"]


def compute_local_tiered_progress(rows: list[dict[str, str | int]], exercise_types: list[str]) -> TieredProgressSummary:
    """Compute tiered progress summary from local rows using all-positive completion rule.

    A word counts as "fully completed" only when ALL participating exercise scores are > 0.
    Missing scores default to 0.
    """
    total_words = len(rows)
    if total_words == 0:
        return TieredProgressSummary(
            total_words=0,
            fully_completed_words=0,
            completion_ratio=0.0,
        )

    fully_completed_words = 0
    for row in rows:
        # Check if ALL exercise types have positive scores
        all_positive = all(int(row.get(f"score_{et}", 0)) > 0 for et in exercise_types)
        if all_positive:
            fully_completed_words += 1

    completion_ratio = fully_completed_words / total_words

    return TieredProgressSummary(
        total_words=total_words,
        fully_completed_words=fully_completed_words,
        completion_ratio=completion_ratio,
    )
