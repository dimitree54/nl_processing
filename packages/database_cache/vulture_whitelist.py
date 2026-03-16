from nl_processing.database_cache.models import CacheStatus

CacheStatus.last_refresh_completed_at  # type: ignore[misc]
CacheStatus.last_flush_completed_at  # type: ignore[misc]

# Cache-specific remote sync/delete protocol methods
export_remote_snapshot
apply_score_delta
delete_word
delete_words
# Protocol parameters
event_id
exercise_type
delta
source_word_ids

row_factory  # noqa: F821
extract  # noqa: F821

__all__ = ["CacheStatus"]
