"""Refresh / flush orchestration for the local cache."""

import asyncio
from datetime import UTC, datetime

from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database_cache.exceptions import CacheSyncError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.logging import get_logger

_log = get_logger("sync")


class CacheSyncer:
    """Coordinates full refresh from remote and flush of pending events back to remote."""

    def __init__(self, local_store: LocalStore, progress_store: ExerciseProgressStore) -> None:
        self._local = local_store
        self._remote = progress_store
        self._refresh_lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Pull a full snapshot from the remote database and rebuild the local cache."""
        if self._refresh_lock.locked():
            return
        async with self._refresh_lock:
            now = datetime.now(tz=UTC).isoformat()
            try:
                await self._local.update_metadata(last_refresh_started_at=now)
                scored_pairs = await self._remote.export_remote_snapshot()
                word_pairs: list[tuple[int, str, str, int, str, str]] = [
                    (
                        sp.source_word_id,
                        sp.pair.source.normalized_form,
                        sp.pair.source.word_type.value,
                        0,
                        sp.pair.target.normalized_form,
                        sp.pair.target.word_type.value,
                    )
                    for sp in scored_pairs
                ]
                scores: dict[tuple[int, str], int] = {}
                for sp in scored_pairs:
                    for exercise_type, score in sp.scores.items():
                        scores[(sp.source_word_id, exercise_type)] = score
                await self._local.rebuild_snapshot(word_pairs, scores)
                await self._local.update_metadata(
                    last_refresh_completed_at=datetime.now(tz=UTC).isoformat(),
                )
            except CacheSyncError:
                raise
            except Exception as exc:
                _log.exception("refresh failed")
                await self._local.update_metadata(last_error=str(exc))
                raise CacheSyncError(str(exc)) from exc

    async def flush(self) -> None:
        """Push pending local score events to the remote database."""
        if self._flush_lock.locked():
            return
        async with self._flush_lock:
            events = await self._local.get_pending_events()
            for evt in events:
                eid = str(evt["event_id"])
                try:
                    await self._remote.apply_score_delta(
                        event_id=eid,
                        source_word_id=int(evt["source_word_id"]),
                        exercise_type=str(evt["exercise_type"]),
                        delta=int(evt["delta"]),
                    )
                    await self._local.mark_event_flushed(eid)
                except Exception as exc:
                    _log.warning("flush failed for event %s: %s", eid, exc)
                    await self._local.mark_event_failed(eid, str(exc))
            await self._local.update_metadata(last_flush_completed_at=datetime.now(tz=UTC).isoformat())
