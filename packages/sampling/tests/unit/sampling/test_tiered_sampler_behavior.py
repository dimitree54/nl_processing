"""Sampling behavior tests for TieredMultiExerciseSampler."""

from collections import Counter

from nl_processing.core.models import WordPair
import pytest

from tests.unit.sampling.tiered_conftest import create_tiered_sampler, make_tiered_candidate


@pytest.mark.asyncio
async def test_sample_returns_word_pair() -> None:
    """sample() returns a single WordPair."""
    sampler = create_tiered_sampler([
        make_tiered_candidate("huis", "dom", scores={"flashcard": -1}),
        make_tiered_candidate("boek", "kniga", scores={"flashcard": 0}),
    ])

    result = await sampler.sample()

    assert isinstance(result, WordPair)


@pytest.mark.asyncio
async def test_sample_empty_candidates_raises_runtime_error() -> None:
    """An empty provider raises RuntimeError."""
    sampler = create_tiered_sampler([])

    with pytest.raises(RuntimeError, match="No word pairs found"):
        await sampler.sample()


@pytest.mark.asyncio
async def test_sample_statistical_weighting_prefers_negative_scores() -> None:
    """Negative scores are sampled more often than non-negative scores."""
    sampler = create_tiered_sampler(
        [
            make_tiered_candidate("negative", "negative_t", scores={"flashcard": -1}),
            make_tiered_candidate("zero", "zero_t", scores={"flashcard": 0}),
            make_tiered_candidate("positive", "positive_t", scores={"flashcard": 5}),
        ],
        finished_exercise_weight=0.01,
    )

    counts: Counter[str] = Counter()
    for _trial in range(1000):
        result = await sampler.sample()
        counts[result.source.normalized_form] += 1

    assert counts["negative"] > counts["zero"]
    assert counts["negative"] > counts["positive"]
