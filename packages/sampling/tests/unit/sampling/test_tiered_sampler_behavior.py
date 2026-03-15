"""Sampling behavior tests for TieredExerciseSampler."""

from collections import Counter

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.core.tiered_models import TieredExerciseSelection
import pytest

from nl_processing.sampling.tiered_sampler import TieredExerciseSampler
from tests.unit.sampling.tiered_conftest import MockTieredCandidateProvider, make_tiered_candidate


@pytest.mark.asyncio
async def test_sample_zero_returns_empty() -> None:
    """sample(0) returns empty list without calling the store."""
    sampler = _create_test_sampler([make_tiered_candidate("huis", "dom")])
    result = await sampler.sample(0)
    assert result == []


@pytest.mark.asyncio
async def test_sample_negative_returns_empty() -> None:
    """sample(-1) returns empty list."""
    sampler = _create_test_sampler([make_tiered_candidate("huis", "dom")])
    result = await sampler.sample(-1)
    assert result == []


def _create_test_sampler(candidates: list) -> TieredExerciseSampler:
    """Helper to create a test sampler with given candidates."""
    mock_store = MockTieredCandidateProvider(candidates)
    return TieredExerciseSampler(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        mode_slug="mixed",
        exercise_types=["flashcard"],
        tiered_store=mock_store,
    )


@pytest.mark.asyncio
async def test_sample_returns_requested_count_when_enough_candidates() -> None:
    """When enough candidates exist, sample(limit) returns exactly limit items."""
    candidates = [make_tiered_candidate(f"w{i}", f"t{i}") for i in range(10)]
    sampler = _create_test_sampler(candidates)
    result = await sampler.sample(5)
    assert len(result) == 5


@pytest.mark.asyncio
async def test_sample_all_when_limit_exceeds_candidates() -> None:
    """When limit > candidates, all candidates are returned."""
    candidates = [make_tiered_candidate(f"w{i}", f"t{i}") for i in range(3)]
    sampler = _create_test_sampler(candidates)
    result = await sampler.sample(100)
    assert len(result) == 3
    forms = {selection.pair.source.normalized_form for selection in result}
    assert forms == {"w0", "w1", "w2"}


@pytest.mark.asyncio
async def test_sample_no_duplicates() -> None:
    """Sampling without replacement produces no duplicates."""
    candidates = [make_tiered_candidate(f"w{i}", f"t{i}") for i in range(20)]
    sampler = _create_test_sampler(candidates)
    result = await sampler.sample(10)
    source_forms = [selection.pair.source.normalized_form for selection in result]
    assert len(source_forms) == len(set(source_forms))


@pytest.mark.asyncio
async def test_sample_empty_candidates() -> None:
    """No candidates in store returns empty list."""
    sampler = _create_test_sampler([])
    result = await sampler.sample(5)
    assert result == []


@pytest.mark.asyncio
async def test_sample_returns_tiered_exercise_selections() -> None:
    """Sampled items are TieredExerciseSelection objects with expected fields."""
    candidates = [
        make_tiered_candidate("huis", "dom", word_type=PartOfSpeech.NOUN),
        make_tiered_candidate("lopen", "begat", word_type=PartOfSpeech.VERB),
    ]
    sampler = _create_test_sampler(candidates)
    result = await sampler.sample(2)

    assert len(result) == 2
    for selection in result:
        assert isinstance(selection, TieredExerciseSelection)
        assert selection.pair.source.language == Language.NL
        assert selection.pair.target.language == Language.RU
        assert selection.exercise_type == "flashcard"
        assert selection.source_word_id >= 1
        assert isinstance(selection.in_repeat_mode, bool)


@pytest.mark.asyncio
async def test_sample_statistical_weighting() -> None:
    """Unfinished words are sampled much more often than fully finished words."""
    unfinished = make_tiered_candidate("unfinished", "unfinished_t", scores={"flashcard": 0})
    finished = make_tiered_candidate("finished", "finished_t", scores={"flashcard": 5})
    mock_store = MockTieredCandidateProvider([unfinished, finished])

    sampler = TieredExerciseSampler(
        user_id="u1",
        source_language=Language.NL,
        target_language=Language.RU,
        mode_slug="mixed",
        exercise_types=["flashcard"],
        finished_word_weight=0.01,
        tiered_store=mock_store,
    )

    counts: Counter[str] = Counter()
    for _trial in range(1000):
        result = await sampler.sample(1)
        counts[result[0].pair.source.normalized_form] += 1

    assert counts["unfinished"] > counts["finished"] * 5
