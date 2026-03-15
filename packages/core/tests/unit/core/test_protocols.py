import asyncio
from typing import get_type_hints

from nl_processing.core.models import Language, PartOfSpeech, ScoredWordPair, Word, WordPair
from nl_processing.core.protocols import ScoredPairProvider


def _build_scored_pair() -> ScoredWordPair:
    """Create one scored pair for protocol contract tests."""
    return ScoredWordPair(
        pair=WordPair(
            source=Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
            target=Word(normalized_form="велосипед", word_type=PartOfSpeech.NOUN, language=Language.RU),
        ),
        scores={"reading": 4},
    )


class _ValidScoredPairProvider:
    """Runtime-checkable provider implementation for contract tests."""

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]:
        """Return one scored pair."""
        return [_build_scored_pair()]


class _MissingScoredPairMethod:
    """Object that does not satisfy the protocol."""


def test_scored_pair_provider_is_runtime_checkable() -> None:
    """Test ScoredPairProvider supports runtime structural checks."""
    assert isinstance(_ValidScoredPairProvider(), ScoredPairProvider)
    assert not isinstance(_MissingScoredPairMethod(), ScoredPairProvider)


def test_scored_pair_provider_return_annotation_matches_contract() -> None:
    """Test ScoredPairProvider exposes the documented return annotation."""
    annotations = get_type_hints(ScoredPairProvider.get_word_pairs_with_scores)
    assert annotations == {"return": list[ScoredWordPair]}


def test_scored_pair_provider_can_return_scored_word_pairs() -> None:
    """Test a ScoredPairProvider implementation returns scored word pairs asynchronously."""
    provider: ScoredPairProvider = _ValidScoredPairProvider()

    result = asyncio.run(provider.get_word_pairs_with_scores())

    assert result == [_build_scored_pair()]
