"""Unit tests for WordSampler weighted single-item sampling."""

from collections import Counter

from nl_processing.core.models import WordPair
from nl_processing.core.protocols import ScoredPairProvider
import pytest

from nl_processing.sampling.service import WordSampler
from tests.unit.sampling.conftest import MockProgressStore, make_scored_pair, patch_store


def test_constructor_preserves_configuration() -> None:
    """Constructor stores injected provider and configured weights."""
    mock_store = MockProgressStore([])
    sampler = WordSampler(
        scored_store=mock_store,
        exercise_type="flashcard",
        positive_balance_weight=0.25,
        negative_balance_weight=7,
    )

    assert sampler._progress_store is mock_store
    assert sampler._exercise_type == "flashcard"
    assert sampler._positive_balance_weight == 0.25
    assert sampler._negative_balance_weight == 7


def test_mock_progress_store_satisfies_protocol() -> None:
    """MockProgressStore structurally satisfies ScoredPairProvider."""
    assert isinstance(MockProgressStore([]), ScoredPairProvider)


@pytest.mark.asyncio
async def test_sample_returns_word_pair(sampler: WordSampler) -> None:
    """sample() returns a single WordPair."""
    patch_store(
        sampler,
        [
            make_scored_pair("huis", "dom", scores={"flashcard": 0}),
            make_scored_pair("boek", "kniga", scores={"flashcard": 0}),
        ],
    )

    result = await sampler.sample()

    assert isinstance(result, WordPair)


@pytest.mark.asyncio
async def test_sample_empty_candidates_raises_runtime_error(sampler: WordSampler) -> None:
    """An empty provider raises RuntimeError."""
    patch_store(sampler, [])

    with pytest.raises(RuntimeError, match="No word pairs found"):
        await sampler.sample()


@pytest.mark.asyncio
async def test_sample_statistical_weighting_prefers_negative_scores() -> None:
    """Negative scores are sampled more often than zero and positive scores."""
    sampler = WordSampler(
        scored_store=MockProgressStore([
            make_scored_pair("negative", "negative_t", scores={"flashcard": -1}),
            make_scored_pair("zero", "zero_t", scores={"flashcard": 0}),
            make_scored_pair("positive", "positive_t", scores={"flashcard": 5}),
        ]),
        exercise_type="flashcard",
        positive_balance_weight=0.01,
        negative_balance_weight=100,
    )

    counts: Counter[str] = Counter()
    for _trial in range(1000):
        result = await sampler.sample()
        counts[result.source.normalized_form] += 1

    assert counts["negative"] > counts["zero"]
    assert counts["zero"] > counts["positive"]
