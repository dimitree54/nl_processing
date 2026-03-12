"""Helper functions extracted from service.py for code organization."""

from datetime import UTC, datetime

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.database.models import ExerciseProgressSummary, PersonalWord


def _parse_dt(meta: dict[str, str | int], key: str) -> datetime | None:
    val = meta[key] if key in meta else None
    if val is None:
        return None
    return datetime.fromisoformat(str(val))


def row_to_word_pair(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
) -> WordPair:
    """Convert database row to WordPair object with explicit language parameters."""
    return WordPair(
        source=Word(
            normalized_form=str(row["source_normalized_form"]),
            word_type=PartOfSpeech(row["source_word_type"]),
            language=source_language,
        ),
        target=Word(
            normalized_form=str(row["target_normalized_form"]),
            word_type=PartOfSpeech(row["target_word_type"]),
            language=target_language,
        ),
    )


def row_to_personal_word(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
    exercise_types: list[str],
) -> PersonalWord:
    """Reconstruct a PersonalWord from a cached row dict."""
    pair = row_to_word_pair(row, source_language, target_language)
    added_at_raw = row.get("added_at")
    added_at = datetime.fromisoformat(str(added_at_raw)) if added_at_raw is not None else datetime.now(tz=UTC)
    scores = {et: int(row.get(f"score_{et}", 0)) for et in exercise_types}
    return PersonalWord(
        pair=pair,
        source_word_id=int(row["source_word_id"]),
        target_word_id=int(row["target_word_id"]),
        added_at=added_at,
        scores=scores,
    )


def compute_local_progress_summary(
    rows: list[dict[str, str | int]],
    exercise_types: list[str],
) -> dict[str, ExerciseProgressSummary]:
    """Compute progress summary from cached rows with flattened score fields."""
    total_words = len(rows)
    if total_words == 0:
        return {
            et: ExerciseProgressSummary(
                total_words=0,
                negative_words=0,
                negative_ratio=0.0,
                negative_percentage=0.0,
            )
            for et in exercise_types
        }
    result: dict[str, ExerciseProgressSummary] = {}
    for et in exercise_types:
        score_key = f"score_{et}"
        negative_words = sum(1 for r in rows if int(r.get(score_key, 0)) < 0)
        negative_ratio = negative_words / total_words
        result[et] = ExerciseProgressSummary(
            total_words=total_words,
            negative_words=negative_words,
            negative_ratio=negative_ratio,
            negative_percentage=negative_ratio * 100,
        )
    return result
