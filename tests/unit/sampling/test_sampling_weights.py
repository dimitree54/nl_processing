"""Unit tests for WordSampler — constructor validation and weighted sampling."""

from collections import Counter

import pytest

from nl_processing.sampling.service import WordSampler
from tests.unit.sampling.conftest import make_scored_pair, patch_store

# ---- constructor validation ----


def test_empty_exercise_types_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty exercise_types list raises ValueError."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    with pytest.raises(ValueError, match="exercise_types must be a non-empty list"):
        WordSampler(user_id="u1", exercise_types=[])


def test_weight_zero_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """positive_balance_weight=0 raises ValueError."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    with pytest.raises(ValueError, match="positive_balance_weight"):
        WordSampler(user_id="u1", exercise_types=["flashcard"], positive_balance_weight=0)


def test_weight_negative_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """positive_balance_weight=-0.5 raises ValueError."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    with pytest.raises(ValueError, match="positive_balance_weight"):
        WordSampler(user_id="u1", exercise_types=["flashcard"], positive_balance_weight=-0.5)


def test_weight_one_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """positive_balance_weight=1.0 is valid (boundary)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    ws = WordSampler(user_id="u1", exercise_types=["flashcard"], positive_balance_weight=1.0)
    assert ws._positive_balance_weight == 1.0


def test_weight_default_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default positive_balance_weight=0.01 is valid."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    ws = WordSampler(user_id="u1", exercise_types=["flashcard"])
    assert ws._positive_balance_weight == 0.01


# ---- sampling behavior ----


@pytest.mark.asyncio
async def test_sample_zero_returns_empty(sampler: WordSampler) -> None:
    """sample(0) returns empty list without calling the store."""
    patch_store(sampler, [make_scored_pair("huis", "dom")])
    result = await sampler.sample(0)
    assert result == []


@pytest.mark.asyncio
async def test_sample_negative_returns_empty(sampler: WordSampler) -> None:
    """sample(-1) returns empty list."""
    patch_store(sampler, [make_scored_pair("huis", "dom")])
    result = await sampler.sample(-1)
    assert result == []


@pytest.mark.asyncio
async def test_sample_returns_at_most_limit(sampler: WordSampler) -> None:
    """Result length never exceeds the requested limit."""
    pairs = [make_scored_pair(f"w{i}", f"t{i}") for i in range(10)]
    patch_store(sampler, pairs)
    result = await sampler.sample(3)
    assert len(result) <= 3


@pytest.mark.asyncio
async def test_sample_all_when_limit_exceeds_candidates(sampler: WordSampler) -> None:
    """When limit > candidates, all candidates are returned."""
    pairs = [make_scored_pair(f"w{i}", f"t{i}") for i in range(3)]
    patch_store(sampler, pairs)
    result = await sampler.sample(100)
    assert len(result) == 3
    forms = {wp.source.normalized_form for wp in result}
    assert forms == {"w0", "w1", "w2"}


@pytest.mark.asyncio
async def test_sample_no_duplicates(sampler: WordSampler) -> None:
    """Sampling without replacement produces no duplicates."""
    pairs = [make_scored_pair(f"w{i}", f"t{i}") for i in range(20)]
    patch_store(sampler, pairs)
    result = await sampler.sample(10)
    source_forms = [wp.source.normalized_form for wp in result]
    assert len(source_forms) == len(set(source_forms))


@pytest.mark.asyncio
async def test_sample_empty_candidates(sampler: WordSampler) -> None:
    """No candidates in store returns empty list."""
    patch_store(sampler, [])
    result = await sampler.sample(5)
    assert result == []


@pytest.mark.asyncio
async def test_sample_statistical_weighting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-positive scored words are sampled much more often than positive scored words."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://dummy:dummy@localhost/dummy")
    ws = WordSampler(user_id="u1", exercise_types=["flashcard"], positive_balance_weight=0.01)
    low = make_scored_pair("low", "low_t", scores={"flashcard": 0})
    high = make_scored_pair("high", "high_t", scores={"flashcard": 5})
    patch_store(ws, [low, high])
    counts: Counter[str] = Counter()
    for _trial in range(1000):
        result = await ws.sample(1)
        counts[result[0].source.normalized_form] += 1
    assert counts["low"] > counts["high"] * 5
