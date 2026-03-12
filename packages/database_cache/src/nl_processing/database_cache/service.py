"""DatabaseCacheService — public API for the local SQLite cache layer."""

import asyncio
from datetime import timedelta
import json
import tempfile
from uuid import uuid4

from nl_processing.core.models import Language, ScoredWordPair, Word, WordPair
from nl_processing.core.ports import RemoteProgressSyncPort
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.models import ExerciseProgressSummary, PersonalWord

from nl_processing.database_cache._service_helpers import (
    background_flush,
    background_refresh,
    compute_local_progress_summary,
    get_cache_status,
    is_stale,
    row_to_personal_word,
    row_to_word_pair,
)
from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.logging import get_logger
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.ports import RemoteDeletePort
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

    async def init(self) -> CacheStatus:
        """Open local store, bootstrap or refresh as needed, return status."""
        progress_store = self._remote_progress or ExerciseProgressStore(
            user_id=self._user_id,
            source_language=self._source_language,
            target_language=self._target_language,
            exercise_types=self._exercise_types,
        )
        if self._remote_db is None:
            from nl_processing.database.service import DatabaseService  # noqa: PLC0415

            self._remote_db = DatabaseService(
                user_id=self._user_id,
                source_language=self._source_language,
                target_language=self._target_language,
            )
        if self._local is None:
            self._local = LocalStore(self._db_path)
        await self._local.open()
        self._syncer = CacheSyncer(self._local, progress_store)
        await self._local.ensure_metadata(self._exercise_types)
        meta = await self._local.get_metadata()
        if meta and json.loads(str(meta["exercise_types"])) != self._exercise_types:
            await self._local.ensure_metadata(self._exercise_types)
            await self._syncer.refresh()
        elif not await self._local.has_snapshot():
            await self._syncer.refresh()
        elif is_stale(meta, self._cache_ttl):
            asyncio.create_task(background_refresh(self._syncer))
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

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]:
        """Return cached word pairs with exercise scores."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
        result: list[ScoredWordPair] = []
        for row in rows:
            pair = row_to_word_pair(row, self._source_language, self._target_language)
            scores = {et: int(row[f"score_{et}"]) for et in self._exercise_types}
            result.append(ScoredWordPair(pair=pair, scores=scores, source_word_id=int(row["source_word_id"])))
        return result

    async def list_personal_words(self) -> list[PersonalWord]:
        """Return personal-vocabulary entries from local cache (FR-7)."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
        return [
            row_to_personal_word(r, self._source_language, self._target_language, self._exercise_types) for r in rows
        ]

    async def get_progress_summary(self) -> dict[str, ExerciseProgressSummary]:
        """Return per-exercise progress stats from cached data (FR-8, DEC-7)."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
        return compute_local_progress_summary(rows, self._exercise_types)

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
        asyncio.create_task(background_flush(self._syncer))

    async def refresh(self) -> None:
        """Trigger a full cache refresh from the remote database."""
        assert self._syncer is not None
        await self._syncer.refresh()

    async def flush(self) -> None:
        """Flush pending score events to the remote database."""
        assert self._syncer is not None
        await self._syncer.flush()

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

    def _ensure_ready(self) -> None:
        if not self._initialized or self._local is None:
            raise CacheNotReadyError("Cache not initialized — call init() first")
