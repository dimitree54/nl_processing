"""Unit tests for WordSampler — adversarial sampling behavior."""

import pytest

from nl_processing.core.models import Language, PartOfSpeech
from nl_processing.sampling.service import WordSampler
from tests.unit.sampling.conftest import make_scored_pair, make_word, patch_store


@pytest.mark.asyncio
async def test_adversarial_same_pos_only(sampler: WordSampler) -> None:
    """Adversarial sampling returns only words with the same part of speech."""
    pairs = [
        make_scored_pair("huis", "dom", word_type=PartOfSpeech.NOUN),
        make_scored_pair("lopen", "begat", word_type=PartOfSpeech.VERB),
        make_scored_pair("boek", "kniga", word_type=PartOfSpeech.NOUN),
    ]
    patch_store(sampler, pairs)
    source = make_word("kat", word_type=PartOfSpeech.NOUN)
    result = await sampler.sample_adversarial(source, 10)
    assert all(wp.source.word_type == PartOfSpeech.NOUN for wp in result)


@pytest.mark.asyncio
async def test_adversarial_excludes_source(sampler: WordSampler) -> None:
    """Source word is excluded from adversarial results."""
    pairs = [
        make_scored_pair("huis", "dom"),
        make_scored_pair("boek", "kniga"),
    ]
    patch_store(sampler, pairs)
    source = make_word("huis")
    result = await sampler.sample_adversarial(source, 10)
    forms = {wp.source.normalized_form for wp in result}
    assert "huis" not in forms


@pytest.mark.asyncio
async def test_adversarial_zero_limit_returns_empty(sampler: WordSampler) -> None:
    """sample_adversarial(limit=0) returns empty list."""
    patch_store(sampler, [make_scored_pair("huis", "dom")])
    source = make_word("kat")
    result = await sampler.sample_adversarial(source, 0)
    assert result == []


@pytest.mark.asyncio
async def test_adversarial_no_matching_pos(sampler: WordSampler) -> None:
    """No words with matching POS returns empty list."""
    pairs = [make_scored_pair("lopen", "begat", word_type=PartOfSpeech.VERB)]
    patch_store(sampler, pairs)
    source = make_word("huis", word_type=PartOfSpeech.NOUN)
    result = await sampler.sample_adversarial(source, 5)
    assert result == []


@pytest.mark.asyncio
async def test_adversarial_fewer_than_limit(sampler: WordSampler) -> None:
    """Fewer candidates than limit returns all matching candidates."""
    pairs = [
        make_scored_pair("huis", "dom"),
        make_scored_pair("boek", "kniga"),
    ]
    patch_store(sampler, pairs)
    source = make_word("kat")
    result = await sampler.sample_adversarial(source, 100)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_adversarial_wrong_language_raises(sampler: WordSampler) -> None:
    """Source word with wrong language raises ValueError."""
    patch_store(sampler, [])
    source = make_word("dom", language=Language.RU)
    with pytest.raises(ValueError, match="does not match"):
        await sampler.sample_adversarial(source, 5)


@pytest.mark.asyncio
async def test_adversarial_no_duplicates(sampler: WordSampler) -> None:
    """Adversarial sampling produces no duplicates."""
    pairs = [make_scored_pair(f"w{i}", f"t{i}") for i in range(20)]
    patch_store(sampler, pairs)
    source = make_word("other")
    result = await sampler.sample_adversarial(source, 10)
    source_forms = [wp.source.normalized_form for wp in result]
    assert len(source_forms) == len(set(source_forms))
