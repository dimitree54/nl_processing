"""Refresh / flush orchestration for the tiered exercise cache."""

import asyncio
from datetime import UTC, datetime

from nl_processing.core.tiered_ports import RemoteTieredSyncPort

from nl_processing.database_cache._tiered_local_store import TieredLocalStore
from nl_processing.database_cache.exceptions import CacheSyncError
from nl_processing.database_cache.logging import get_logger

_log = get_logger("tiered_sync")


class TieredCacheSyncer:
    """Coordinates full refresh from remote and flush of pending events for tiered cache."""

    def __init__(self, local_store: TieredLocalStore, remote: RemoteTieredSyncPort) -> None:
        self._local = local_store
        self._remote = remote
        self._refresh_lock = asyncio.Lock()
        self._flush_lock = asyncio.Lock()

    async def refresh(self) -> None:
        """Pull a full tiered snapshot from remote and rebuild the local cache."""
        if self._refresh_lock.locked():
            return
        async with self._refresh_lock:
            now = datetime.now(tz=UTC).isoformat()
            try:
                await self._local.update_tiered_metadata(last_refresh_started_at=now)
                snapshot_entries = await self._remote.export_tiered_snapshot()

                # Convert snapshot entries to local format
                word_pairs: list[tuple[int, str, str, int, str, str]] = []
                scores: dict[tuple[int, str], int] = {}
                repeat_states: dict[tuple[str, int], str] = {}

                for entry in snapshot_entries:
                    # Word pair data
                    word_pairs.append((
                        entry.source_word_id,
                        entry.pair.source.normalized_form,
                        entry.pair.source.word_type.value,
                        entry.target_word_id,
                        entry.pair.target.normalized_form,
                        entry.pair.target.word_type.value,
                    ))

                    # Scores
                    for exercise_type, score in entry.scores.items():
                        scores[(entry.source_word_id, exercise_type)] = score

                    # Repeat states (we need mode_slug from metadata for this)
                    if entry.in_repeat_mode:
                        metadata = await self._local.get_tiered_metadata()
                        mode_slug = metadata["mode_slug"] if metadata else "default"
                        repeat_states[(mode_slug, entry.source_word_id)] = now

                await self._local.rebuild_tiered_snapshot(word_pairs, scores, repeat_states)
                await self._local.update_tiered_metadata(last_refresh_completed_at=datetime.now(tz=UTC).isoformat())

            except CacheSyncError:
                raise
            except Exception as exc:
                _log.exception("tiered refresh failed")
                await self._local.update_tiered_metadata(last_error=str(exc))
                raise CacheSyncError(str(exc)) from exc

    async def flush(self, *, skip_if_running: bool = False) -> None:
        """Push pending tiered events to remote database.

        Args:
            skip_if_running: If True, return immediately if another flush is already running.
                           If False (default), wait for any running flush to complete.
        """
        if skip_if_running and self._flush_lock.locked():
            return
        async with self._flush_lock:
            events = await self._local.get_tiered_pending_events()
            for evt in events:
                eid = str(evt["event_id"])
                try:
                    await self._remote.apply_tiered_result(
                        event_id=eid,
                        source_word_id=int(evt["source_word_id"]),
                        exercise_type=str(evt["exercise_type"]),
                        delta=int(evt["delta"]),
                    )
                    await self._local.mark_tiered_event_flushed(eid)
                except Exception as exc:
                    _log.warning("tiered flush failed for event %s: %s", eid, exc)
                    await self._local.mark_tiered_event_failed(eid, str(exc))
            await self._local.update_tiered_metadata(last_flush_completed_at=datetime.now(tz=UTC).isoformat())
