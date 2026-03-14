"""Helper functions for TieredExerciseCacheService."""

from datetime import UTC, datetime, timedelta

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.core.tiered_models import TieredCandidate

from nl_processing.database_cache.logging import get_logger
from nl_processing.database_cache.tiered_sync import TieredCacheSyncer

_log = get_logger("tiered_cache_helpers")


def parse_dt_meta(meta: dict[str, str | int], key: str) -> datetime | None:
    """Parse datetime from metadata (reused pattern from service helpers)."""
    val = meta[key] if key in meta else None
    if val is None:
        return None
    return datetime.fromisoformat(str(val))


def is_tiered_stale(meta: dict[str, str | int] | None, cache_ttl: timedelta) -> bool:
    """Check if tiered cache is stale."""
    if not meta:
        return True
    last_refresh = parse_dt_meta(meta, "last_refresh_completed_at")
    if last_refresh is None:
        return True
    return datetime.now(tz=UTC) - last_refresh > cache_ttl


async def background_tiered_refresh(syncer: TieredCacheSyncer) -> None:
    """Background refresh task with error handling."""
    try:
        await syncer.refresh()
    except Exception:
        _log.exception("background tiered refresh failed")


async def background_tiered_flush(syncer: TieredCacheSyncer) -> None:
    """Background flush task with error handling."""
    try:
        await syncer.flush(skip_if_running=True)
    except Exception:
        _log.exception("background tiered flush failed")


def row_to_tiered_candidate(
    row: dict[str, str | int], source_language: Language, target_language: Language
) -> TieredCandidate:
    """Convert database row to TieredCandidate."""
    pair = WordPair(
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

    # Extract scores (fields like score_exercise1, score_exercise2, etc.)
    scores = {}
    in_repeat_mode = bool(row["in_repeat_mode"])
    for key, value in row.items():
        if key.startswith("score_"):
            exercise_type = key[6:]  # Remove "score_" prefix
            scores[exercise_type] = int(value)

    return TieredCandidate(
        pair=pair,
        source_word_id=int(row["source_word_id"]),
        scores=scores,
        in_repeat_mode=in_repeat_mode,
    )
