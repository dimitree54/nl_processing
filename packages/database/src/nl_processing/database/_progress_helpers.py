"""Helper functions for progress calculation."""

from nl_processing.database.models import ExerciseProgressSummary


def compute_progress_summary(
    rows: list[dict],
    scores_by_word: dict[int, dict[str, int]],
    exercise_types: list[str],
) -> dict[str, ExerciseProgressSummary]:
    """Compute progress summary for given rows and scores."""
    if not rows:
        return {
            et: ExerciseProgressSummary(
                total_words=0,
                negative_words=0,
                negative_ratio=0.0,
                negative_percentage=0.0,
            )
            for et in exercise_types
        }

    result = {}
    total_words = len(rows)

    for exercise_type in exercise_types:
        negative_words = 0
        for row in rows:
            source_word_id = int(row["source_id"])  # type: ignore[arg-type]
            score = scores_by_word.get(source_word_id, {}).get(exercise_type, 0)
            if score < 0:
                negative_words += 1

        negative_ratio = negative_words / total_words if total_words > 0 else 0.0
        negative_percentage = negative_ratio * 100

        result[exercise_type] = ExerciseProgressSummary(
            total_words=total_words,
            negative_words=negative_words,
            negative_ratio=negative_ratio,
            negative_percentage=negative_percentage,
        )

    return result
