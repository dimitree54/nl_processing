"""Integration tests for WordSampler weighted sampling against real Neon PostgreSQL."""

import pytest

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.database.models import WordPair
from nl_processing.sampling.service import WordSampler

_EXERCISE_TYPES = ["nl_to_ru"]


def _make_sampler(user_id: str) -> WordSampler:
    return WordSampler(user_id=user_id, exercise_types=_EXERCISE_TYPES)


@pytest.mark.asyncio
async def test_sample_returns_requested_count(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample(5) returns exactly 5 unique WordPairs from the test user's dictionary."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    result = await sampler.sample(5)
    assert len(result) == 5
    forms = {wp.source.normalized_form for wp in result}
    assert len(forms) == 5


@pytest.mark.asyncio
async def test_sample_with_all_zero_scores_returns_items(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample returns items when scores are zero for a configured exercise type."""
    sampler = WordSampler(
        user_id=str(populated_db["user_id"]),
        exercise_types=["nl_to_ru"],
    )
    result = await sampler.sample(3)
    assert len(result) == 3
    assert all(isinstance(wp, WordPair) for wp in result)


@pytest.mark.asyncio
async def test_sample_favors_non_positive_scored_words(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """Words with non-positive scores are sampled >3x more than positive-scored words."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    zero_words = set(populated_db["zero_scored_words"])  # type: ignore[arg-type]
    positive_words = set(populated_db["positive_scored_words"])  # type: ignore[arg-type]
    zero_count = 0
    positive_count = 0
    for _trial in range(500):
        result = await sampler.sample(1)
        form = result[0].source.normalized_form
        if form in zero_words:
            zero_count += 1
        elif form in positive_words:
            positive_count += 1
    assert zero_count > positive_count * 3, (
        f"Expected zero_count ({zero_count}) > 3 * positive_count ({positive_count})"
    )


@pytest.mark.asyncio
async def test_sample_exceeding_dictionary_returns_all(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample(100) when user has only 10 words returns all 10."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    total = int(populated_db["total_words"])
    result = await sampler.sample(100)
    assert len(result) == total


@pytest.mark.asyncio
async def test_sample_zero_returns_empty(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample(0) returns empty list."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    result = await sampler.sample(0)
    assert result == []


@pytest.mark.asyncio
async def test_returned_word_pairs_have_correct_fields(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """Returned WordPairs have correct Word fields (language, word_type, normalized_form)."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    result = await sampler.sample(10)
    valid_pos = {PartOfSpeech.NOUN, PartOfSpeech.VERB, PartOfSpeech.ADJECTIVE}
    for wp in result:
        assert wp.source.language == Language.NL
        assert wp.target.language == Language.RU
        assert wp.source.word_type in valid_pos
        assert wp.target.word_type in valid_pos
        assert len(wp.source.normalized_form) > 0
        assert len(wp.target.normalized_form) > 0


@pytest.mark.asyncio
async def test_sample_returns_no_duplicates(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """Sampling without replacement produces no duplicates."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    result = await sampler.sample(8)
    forms = [wp.source.normalized_form for wp in result]
    assert len(forms) == len(set(forms))
