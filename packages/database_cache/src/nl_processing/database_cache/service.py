"""DatabaseCacheService — public API for the local SQLite cache layer."""

import asyncio
from datetime import UTC, datetime, timedelta
import json
import tempfile
from uuid import uuid4

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair
from nl_processing.database.exercise_progress import ExerciseProgressStore

from nl_processing.database_cache.exceptions import CacheNotReadyError
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.logging import get_logger
from nl_processing.database_cache.models import CacheStatus
from nl_processing.database_cache.sync import CacheSyncer

_log = get_logger("service")


class DatabaseCacheService:
    """Offline-first cache backed by a local SQLite database."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language,
        target_language: Language,
        exercise_types: list[str],
        cache_ttl: timedelta,
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
        self._initialized = False
        self._local: LocalStore | None = None
        self._syncer: CacheSyncer | None = None

    async def init(self) -> CacheStatus:
        """Open local store, bootstrap or refresh as needed, return status."""
        progress_store = ExerciseProgressStore(
            user_id=self._user_id,
            source_language=self._source_language,
            target_language=self._target_language,
            exercise_types=self._exercise_types,
        )
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
        elif self._is_stale(meta):
            asyncio.create_task(self._background_refresh())
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
        return [self._row_to_word_pair(r) for r in rows]

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]:
        """Return cached word pairs with exercise scores."""
        self._ensure_ready()
        assert self._local is not None
        rows = await self._local.get_cached_word_pairs_with_scores(self._exercise_types)
        result: list[ScoredWordPair] = []
        for row in rows:
            pair = self._row_to_word_pair(row)
            scores = {et: int(row[f"score_{et}"]) for et in self._exercise_types}
            result.append(ScoredWordPair(pair=pair, scores=scores, source_word_id=int(row["source_word_id"])))
        return result

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
        asyncio.create_task(self._background_flush())

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
        meta = await self._local.get_metadata()
        has_snap = await self._local.has_snapshot()
        pending = await self._local.get_pending_event_count()
        last_refresh = _parse_dt(meta, "last_refresh_completed_at") if meta else None
        last_flush = _parse_dt(meta, "last_flush_completed_at") if meta else None
        return CacheStatus(
            is_ready=self._initialized and has_snap,
            is_stale=self._is_stale(meta),
            has_snapshot=has_snap,
            pending_events=pending,
            last_refresh_completed_at=last_refresh,
            last_flush_completed_at=last_flush,
        )

    def _ensure_ready(self) -> None:
        if not self._initialized or self._local is None:
            raise CacheNotReadyError("Cache not initialized — call init() first")

    def _is_stale(self, meta: dict[str, str | int] | None) -> bool:
        if not meta:
            return True
        last_refresh = _parse_dt(meta, "last_refresh_completed_at")
        if last_refresh is None:
            return True
        return datetime.now(tz=UTC) - last_refresh > self._cache_ttl

    def _row_to_word_pair(self, row: dict[str, str | int]) -> WordPair:
        return WordPair(
            source=Word(
                normalized_form=str(row["source_normalized_form"]),
                word_type=PartOfSpeech(row["source_word_type"]),
                language=self._source_language,
            ),
            target=Word(
                normalized_form=str(row["target_normalized_form"]),
                word_type=PartOfSpeech(row["target_word_type"]),
                language=self._target_language,
            ),
        )

    async def _background_refresh(self) -> None:
        try:
            assert self._syncer is not None
            await self._syncer.refresh()
        except Exception:
            _log.exception("background refresh failed")

    async def _background_flush(self) -> None:
        try:
            assert self._syncer is not None
            await self._syncer.flush(skip_if_running=True)
        except Exception:
            _log.exception("background flush failed")


def _parse_dt(meta: dict[str, str | int], key: str) -> datetime | None:
    val = meta[key] if key in meta else None
    if val is None:
        return None
    return datetime.fromisoformat(str(val))
