from datetime import datetime

from pydantic import BaseModel


class CacheStatus(BaseModel):
    is_ready: bool
    is_stale: bool
    has_snapshot: bool
    pending_events: int
    last_refresh_completed_at: datetime | None
    last_flush_completed_at: datetime | None
