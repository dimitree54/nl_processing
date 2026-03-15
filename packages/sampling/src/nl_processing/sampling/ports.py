"""Sampling-local provider protocols."""

from typing import Protocol, runtime_checkable

from nl_processing.core.models import ScoredWordPair


@runtime_checkable
class ScoredPairProvider(Protocol):
    """Provider that returns scored word pairs for sampling."""

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...
