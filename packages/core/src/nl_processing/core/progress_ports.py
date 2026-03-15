"""Progress sync and remote delete ports for cross-package contracts."""

from typing import Protocol, runtime_checkable

from nl_processing.core.progress_models import EnrichedWordPairSnapshot


@runtime_checkable
class RemoteProgressSyncPort(Protocol):
    """Port for remote progress synchronization."""

    async def export_remote_snapshot(self) -> list[EnrichedWordPairSnapshot]: ...

    async def apply_score_delta(
        self,
        *,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None: ...


@runtime_checkable
class RemoteDeletePort(Protocol):
    """Port for remote deletion operations."""

    async def delete_word(self, *, source_word_id: int) -> None: ...

    async def delete_words(self, *, source_word_ids: list[int]) -> None: ...
