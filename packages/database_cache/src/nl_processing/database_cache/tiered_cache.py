"""TieredExerciseCacheService — public API for the tiered exercise cache layer."""

import asyncio
from datetime import timedelta
import json
import tempfile

from nl_processing.core.models import Language
from nl_processing.core.tiered_models import TieredCandidate, TieredProgressSummary
from nl_processing.core.tiered_ports import RemoteTieredSyncPort

from nl_processing.database_cache._tiered_cache_helpers import (
    background_tiered_refresh,
    is_tiered_stale,
    parse_dt_meta,
    row_to_tiered_candidate,
)
from nl_processing.database_cache._tiered_helpers import (
    compute_local_tiered_progress,
    validate_repeat_state_integrity,
)
from nl_processing.database_cache._tiered_local_store import TieredLocalStore
from nl_processing.database_cache._tiered_result_recorder import record_tiered_result_impl
from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.tiered_sync import TieredCacheSyncer


class TieredExerciseCacheService:
    """Offline-first tiered exercise cache backed by SQLite and a compatible remote sync port."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        mode_slug: str,
        exercise_types: list[str],
        cache_ttl: timedelta,
        remote_tiered_progress: RemoteTieredSyncPort | None = None,
        local_store: TieredLocalStore | None = None,
        cache_dir: str | None = None,
    ) -> None:
        if not mode_slug:
            msg = "mode_slug must be a non-empty string"
            raise ValueError(msg)
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)

        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        self._mode_slug = mode_slug
        self._exercise_types = list(exercise_types)
        self._cache_ttl = cache_ttl

        # Pair-scoped cache file (not user-scoped)
        base = cache_dir or tempfile.gettempdir()
        self._db_path = f"{base}/tiered_{user_id}_{source_language.value}_{target_language.value}_{mode_slug}.db"

        self._remote_tiered_progress = remote_tiered_progress
        self._initialized = False
        self._local: TieredLocalStore | None = local_store
        self._syncer: TieredCacheSyncer | None = None

    async def init(self) -> CacheStatus:
        """Open local store, bootstrap or refresh as needed, return status."""
        # Initialize remote if not provided
        if self._remote_tiered_progress is None:
            from nl_processing.database.tiered_exercise_progress import TieredExerciseProgressStore  # noqa: PLC0415

            self._remote_tiered_progress = TieredExerciseProgressStore(
                user_id=self._user_id,
                source_language=self._source_language,
                target_language=self._target_language,
                mode_slug=self._mode_slug,
                exercise_types=self._exercise_types,
            )

        # Initialize local store
        if self._local is None:
            self._local = TieredLocalStore(self._db_path)
        await self._local.open()
        self._syncer = TieredCacheSyncer(self._local, self._remote_tiered_progress)

        # Ensure metadata
        await self._local.ensure_tiered_metadata(self._mode_slug, self._exercise_types)
        meta = await self._local.get_tiered_metadata()

        # Check if refresh is needed
        if meta and json.loads(str(meta["exercise_types"])) != self._exercise_types:
            await self._local.ensure_tiered_metadata(self._mode_slug, self._exercise_types)
            await self._syncer.refresh()
        elif not await self._local.has_tiered_snapshot():
            await self._syncer.refresh()
        elif is_tiered_stale(meta, self._cache_ttl):
            asyncio.create_task(background_tiered_refresh(self._syncer))

        self._initialized = True
        return await self.get_status()

    async def get_tiered_candidates(self) -> list[TieredCandidate]:
        """Return tiered candidates from local store, validating repeat-state integrity."""
        self._ensure_ready()
        assert self._local is not None

        rows = await self._local.get_tiered_candidates(self._mode_slug, self._exercise_types)
        candidates = []

        for row in rows:
            candidate = row_to_tiered_candidate(row, self._source_language, self._target_language)
            # Validate repeat-state integrity
            validate_repeat_state_integrity(candidate.in_repeat_mode, candidate.scores, self._exercise_types)
            candidates.append(candidate)

        return candidates

    async def get_tiered_progress_summary(self) -> TieredProgressSummary:
        """Compute mixed progress summary from local candidates."""
        self._ensure_ready()
        assert self._local is not None

        rows = await self._local.get_tiered_candidates(self._mode_slug, self._exercise_types)
        return compute_local_tiered_progress(rows, self._exercise_types)

    async def record_tiered_result(self, *, source_word_id: int, exercise_type: str, delta: int) -> None:
        """Record a tiered result locally and queue for remote flush."""
        self._ensure_ready()
        assert self._local is not None

        # Validate inputs
        if exercise_type not in self._exercise_types:
            msg = f"Unknown exercise_type '{exercise_type}'; expected one of {sorted(self._exercise_types)}"
            raise ValueError(msg)
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)

        # Record result using helper
        assert self._syncer is not None
        await record_tiered_result_impl(
            self._local, self._syncer, self._mode_slug, self._exercise_types, source_word_id, exercise_type, delta
        )

    async def refresh(self) -> None:
        """Trigger a full cache refresh from the remote database."""
        assert self._syncer is not None
        await self._syncer.refresh()

    async def flush(self) -> None:
        """Flush pending score events to the remote database."""
        assert self._syncer is not None
        await self._syncer.flush()

    async def get_status(self) -> CacheStatus:
        """Build current cache status from metadata and pending events."""
        assert self._local is not None

        meta = await self._local.get_tiered_metadata()
        has_snap = await self._local.has_tiered_snapshot()
        pending = await self._local.get_tiered_pending_event_count()
        last_refresh = parse_dt_meta(meta, "last_refresh_completed_at") if meta else None
        last_flush = parse_dt_meta(meta, "last_flush_completed_at") if meta else None

        return CacheStatus(
            is_ready=self._initialized and has_snap,
            is_stale=is_tiered_stale(meta, self._cache_ttl),
            has_snapshot=has_snap,
            pending_events=pending,
            last_refresh_completed_at=last_refresh,
            last_flush_completed_at=last_flush,
        )

    def _ensure_ready(self) -> None:
        if not self._initialized or self._local is None:
            raise CacheNotReadyError("Tiered cache not initialized — call init() first")
