"""Integration tests for WordSampler adversarial sampling against real Neon PostgreSQL."""

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.sampling.service import WordSampler

_EXERCISE_TYPES = ["nl_to_ru"]


def _make_sampler(user_id: str) -> WordSampler:
    return WordSampler(user_id=user_id, exercise_types=_EXERCISE_TYPES)


def _make_word(
    normalized_form: str,
    word_type: PartOfSpeech = PartOfSpeech.NOUN,
) -> Word:
    return Word(normalized_form=normalized_form, word_type=word_type, language=Language.NL)


@pytest.mark.asyncio
async def test_adversarial_returns_only_same_pos(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample_adversarial(noun_word, 3) returns only noun WordPairs."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    source = _make_word("ander_zelfstandig_naamwoord", PartOfSpeech.NOUN)
    result = await sampler.sample_adversarial(source, 3)
    assert len(result) == 3
    assert all(wp.source.word_type == PartOfSpeech.NOUN for wp in result)


@pytest.mark.asyncio
async def test_adversarial_excludes_source_word(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample_adversarial excludes the source word from results."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    source = _make_word("huis", PartOfSpeech.NOUN)
    result = await sampler.sample_adversarial(source, 10)
    forms = {wp.source.normalized_form for wp in result}
    assert "huis" not in forms
    assert len(result) == 4


@pytest.mark.asyncio
async def test_adversarial_returns_available_when_fewer_than_limit(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample_adversarial(verb_word, 100) with only 2 other verbs returns 2."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    source = _make_word("lopen", PartOfSpeech.VERB)
    result = await sampler.sample_adversarial(source, 100)
    assert len(result) == 2
    assert all(wp.source.word_type == PartOfSpeech.VERB for wp in result)
    forms = {wp.source.normalized_form for wp in result}
    assert forms == {"lezen", "schrijven"}


@pytest.mark.asyncio
async def test_adversarial_no_matching_pos_returns_empty(
    populated_db: dict[str, str | int | list[str] | dict[str, int]],
) -> None:
    """sample_adversarial with no matching POS returns empty list."""
    sampler = _make_sampler(str(populated_db["user_id"]))
    source = _make_word("snel", PartOfSpeech.ADVERB)
    result = await sampler.sample_adversarial(source, 5)
    assert result == []
