"""Service operations for DatabaseCacheService."""

from datetime import timedelta
import json

from nl_processing.core.models import Language
from nl_processing.database.exercise_progress import ExerciseProgressStore

from nl_processing.database_cache._service_helpers import background_refresh, is_stale
from nl_processing.database_cache.local_store import LocalStore
from nl_processing.database_cache.ports import RemoteDeletePort, RemoteProgressSyncPort
from nl_processing.database_cache.sync import CacheSyncer


async def setup_dependencies(
    user_id: str,
    source_language: Language,
    target_language: Language,
    exercise_types: list[str],
    remote_progress: RemoteProgressSyncPort | None,
    remote_db: RemoteDeletePort | None,
    local_store: LocalStore | None,
    db_path: str,
) -> tuple[LocalStore, CacheSyncer, RemoteDeletePort]:
    """Initialize dependencies and connections."""
    progress_store = remote_progress or ExerciseProgressStore(
        user_id=user_id,
        source_language=source_language,
        target_language=target_language,
        exercise_types=exercise_types,
    )

    remote_db_instance = remote_db
    if remote_db_instance is None:
        from nl_processing.database.service import DatabaseService  # noqa: PLC0415

        remote_db_instance = DatabaseService(
            user_id=user_id,
            source_language=source_language,
            target_language=target_language,
        )

    local = local_store
    if local is None:
        local = LocalStore(db_path)
    await local.open()
    syncer = CacheSyncer(local, progress_store)

    return local, syncer, remote_db_instance


async def setup_cache_state(
    local: LocalStore,
    syncer: CacheSyncer,
    exercise_types: list[str],
    cache_ttl: timedelta,
    task_manager: object,
) -> None:
    """Setup cache metadata and determine if refresh is needed."""
    await local.ensure_metadata(exercise_types)
    meta = await local.get_metadata()
    if meta and json.loads(str(meta["exercise_types"])) != exercise_types:
        await local.ensure_metadata(exercise_types)
        await syncer.refresh()
    elif not await local.has_snapshot():
        await syncer.refresh()
    elif is_stale(meta, cache_ttl):
        task_manager.create_task(background_refresh(syncer))
