"""DatabaseCacheService — public API for the local SQLite cache layer."""

from datetime import timedelta
import tempfile
from uuid import uuid4

from nl_processing.core.models import Language, Word, WordPair, WordPairSnapshot

from nl_processing.database_cache._service_helpers import (
    _background_task_with_logging,
    background_flush,
    get_cache_status,
    row_to_word_pair,
    row_to_word_pair_snapshot,
)
from nl_processing.database_cache._service_operations import setup_cache_state, setup_dependencies
from nl_processing.database_cache._task_manager import BackgroundTaskManager
from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.logging import get_logger
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.ports import RemoteDeletePort, RemoteProgressSyncPort
from nl_processing.database_cache.sync import CacheSyncer

_log = get_logger("service")


class DatabaseCacheService:
    """Offline-first cache backed by SQLite and a compatible remote sync port."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
        cache_ttl: timedelta,
        remote_progress: RemoteProgressSyncPort | None = None,
        remote_db: RemoteDeletePort | None = None,
        local_store: LocalStore | None = None,
        cache_dir: str | None = None,
    ) -> None:
        if not exercise_types:
            msg = "exercise_types must be a non-empty list"
            raise ValueError(msg)
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        self._exercise_types = list(exercise_types)
        self._cache_ttl = cache_ttl
        base = cache_dir or tempfile.gettempdir()
        self._db_path = f"{base}/{user_id}_{source_language.value}_{target_language.value}.db"
        self._remote_progress = remote_progress
        self._remote_db = remote_db
        self._initialized = False
        self._local: LocalStore | None = local_store
        self._syncer: CacheSyncer | None = None
        self._task_manager = BackgroundTaskManager()

    async def init(self) -> CacheStatus:
        """Open local store, bootstrap or refresh as needed, return status."""
        self._local, self._syncer, self._remote_db = await setup_dependencies(
            self._user_id,
            self._source_language,
            self._target_language,
            self._exercise_types,
            self._remote_progress,
            self._remote_db,
            self._local,
            self._db_path,
        )
        await setup_cache_state(
            self._local,
            self._syncer,
            self._exercise_types,
            self._cache_ttl,
            self._task_manager,
        )
        self._initialized = True
        return await self.get_status()

    async def get_words(
        self,
        *,
        word_type: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Return cached word pairs, optionally filtered."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs(word_type=word_type, limit=limit, random=random)
        return [row_to_word_pair(r, self._source_language, self._target_language) for r in rows]

    async def get_word_pairs_with_scores(self) -> list[WordPairSnapshot]:
        """Return cached word pairs with current scores (FR-3)."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
        return [
            row_to_word_pair_snapshot(row, self._source_language, self._target_language, self._exercise_types)
            for row in rows
        ]

    async def record_exercise_result(self, *, source_word: Word, exercise_type: str, delta: int) -> None:
        """Record a score change locally and queue for remote flush."""
        self._ensure_ready()
        assert self._local is not None
        if exercise_type not in self._exercise_types:
            msg = f"Unknown exercise_type '{exercise_type}'; expected one of {sorted(self._exercise_types)}"
            raise ValueError(msg)
        if delta not in (1, -1):
            msg = f"delta must be +1 or -1, got {delta}"
            raise ValueError(msg)
        wid = await self._local.get_source_word_id(source_word.normalized_form, source_word.word_type.value)
        if wid is None:
            msg = f"Word '{source_word.normalized_form}' not found in cache"
            raise ValueError(msg)
        await self._local.record_score_and_event(wid, exercise_type, delta, str(uuid4()))
        assert self._syncer is not None
        self._task_manager.create_task(background_flush(self._syncer))

    async def refresh(self) -> None:
        """Trigger a full cache refresh from the remote database."""
        assert self._syncer is not None
        await _background_task_with_logging(self._syncer.refresh(), "refresh")

    async def flush(self) -> None:
        """Flush pending score events to the remote database."""
        assert self._syncer is not None
        await _background_task_with_logging(self._syncer.flush(), "flush")

    async def delete_word(self, source_word_id: int) -> None:
        """Delete a word: remote first, then prune local state (FR-9, DEC-6)."""
        self._ensure_ready()
        assert self._local is not None
        assert self._remote_db is not None
        await self._remote_db.delete_word(source_word_id, exercise_types=self._exercise_types)
        await self._local.delete_cached_word(source_word_id)

    async def delete_words(self, source_word_ids: list[int]) -> None:
        """Delete multiple words: remote first, then prune local state (FR-9)."""
        self._ensure_ready()
        assert self._local is not None
        assert self._remote_db is not None
        await self._remote_db.delete_words(source_word_ids, exercise_types=self._exercise_types)
        for wid in source_word_ids:
            await self._local.delete_cached_word(wid)

    async def get_status(self) -> CacheStatus:
        """Build current cache status from metadata and pending events."""
        assert self._local is not None
        return await get_cache_status(self._local, self._initialized, self._cache_ttl)

    async def close(self) -> None:
        """Close the service and clean up all resources."""
        # Cancel and wait for all background tasks to complete
        await self._task_manager.close()

        # Close the local store
        if self._local is not None:
            await self._local.close()
        # Reset state
        self._initialized = False
        self._local = None
        self._syncer = None

    def _ensure_ready(self) -> None:
        if not self._initialized or self._local is None:
            raise CacheNotReadyError("Cache not initialized — call init() first")
