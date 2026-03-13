from typing import Protocol, runtime_checkable

from nl_processing.core.tiered_models import TieredCandidate, TieredSnapshotEntry


@runtime_checkable
class TieredCandidateProvider(Protocol):
    """Provider of tiered exercise candidates for sampling flows."""

    async def get_tiered_candidates(self) -> list[TieredCandidate]: ...


@runtime_checkable
class RemoteTieredSyncPort(Protocol):
    """Remote sync contract for tiered exercise system."""

    async def export_tiered_snapshot(self) -> list[TieredSnapshotEntry]: ...

    async def apply_tiered_result(
        self, *, event_id: str, source_word_id: int, exercise_type: str, delta: int
    ) -> None: ...
