"""Helper functions extracted from service.py for code organization."""

from collections.abc import Awaitable
from datetime import UTC, datetime, timedelta

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.database.models import ExerciseProgressSummary, PersonalWord

from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.logging import get_logger
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.sync import CacheSyncer

_log = get_logger("service_helpers")


def _parse_dt(meta: dict[str, str | int], key: str) -> datetime | None:
    val = meta[key] if key in meta else None
    if val is None:
        return None
    return datetime.fromisoformat(str(val))


def _create_word_pair_from_row(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
) -> WordPair:
    """Shared helper to convert database row to WordPair object."""
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


def row_to_word_pair(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
) -> WordPair:
    """Convert database row to WordPair object with explicit language parameters."""
    return _create_word_pair_from_row(row, source_language, target_language)


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


async def _background_task_with_logging(coro: Awaitable[None], task_name: str) -> None:
    """Generic background task runner with error logging."""
    try:
        await coro
    except Exception:
        _log.exception(f"background {task_name} failed")


async def background_refresh(syncer: CacheSyncer) -> None:
    """Background refresh task with error handling."""
    await _background_task_with_logging(syncer.refresh(), "refresh")


async def background_flush(syncer: CacheSyncer) -> None:
    """Background flush task with error handling."""
    await _background_task_with_logging(syncer.flush(skip_if_running=True), "flush")


def is_stale(meta: dict[str, str | int] | None, cache_ttl: timedelta) -> bool:
    """Check if cache is stale based on metadata and TTL."""
    if not meta:
        return True
    last_refresh = _parse_dt(meta, "last_refresh_completed_at")
    if last_refresh is None:
        return True
    return datetime.now(tz=UTC) - last_refresh > cache_ttl


async def get_cache_status(
    local: LocalStore,
    initialized: bool,
    cache_ttl: timedelta,
) -> CacheStatus:
    """Build current cache status from metadata and pending events."""
    meta = await local.get_metadata()
    has_snap = await local.has_snapshot()
    pending = await local.get_pending_event_count()
    last_refresh = _parse_dt(meta, "last_refresh_completed_at") if meta else None
    last_flush = _parse_dt(meta, "last_flush_completed_at") if meta else None
    return CacheStatus(
        is_ready=initialized and has_snap,
        is_stale=is_stale(meta, cache_ttl),
        has_snapshot=has_snap,
        pending_events=pending,
        last_refresh_completed_at=last_refresh,
        last_flush_completed_at=last_flush,
    )
