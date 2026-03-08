from typing import Protocol, runtime_checkable

from nl_processing.core.models import ScoredWordPair, WordPairSnapshot


@runtime_checkable
class ScoredPairProvider(Protocol):
    """Provider of score-aware word pairs for sampling or practice flows."""

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...


@runtime_checkable
class RemoteProgressSyncPort(Protocol):
    """Remote sync contract consumed by the local cache layer."""

    async def export_remote_snapshot(self) -> list[WordPairSnapshot]: ...

    async def apply_score_delta(
        self,
        event_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> None: ...
