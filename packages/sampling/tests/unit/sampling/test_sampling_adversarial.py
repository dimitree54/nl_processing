"""Unit tests for the remaining sample_adversarial carryover behavior."""

from nl_processing.core.models import Language, PartOfSpeech
import pytest

from nl_processing.sampling.service import WordSampler
from tests.unit.sampling.conftest import make_scored_pair, make_word, patch_store


@pytest.mark.asyncio
async def test_adversarial_requires_source_language_context(sampler: WordSampler) -> None:
    """Fresh samplers raise because source-language context is not initialized."""
    patch_store(sampler, [make_scored_pair("huis", "dom")])

    with pytest.raises(AttributeError, match="_source_language"):
        await sampler.sample_adversarial(make_word("kat"), 1)


@pytest.mark.asyncio
async def test_adversarial_same_pos_only_when_context_injected(sampler: WordSampler) -> None:
    """With source-language context injected, only same-POS distractors are returned."""
    sampler._source_language = Language.NL
    patch_store(
        sampler,
        [
            make_scored_pair("huis", "dom", word_type=PartOfSpeech.NOUN),
            make_scored_pair("lopen", "begat", word_type=PartOfSpeech.VERB),
            make_scored_pair("boek", "kniga", word_type=PartOfSpeech.NOUN),
        ],
    )

    result = await sampler.sample_adversarial(make_word("kat", word_type=PartOfSpeech.NOUN), 10)

    assert all(word_pair.source.word_type == PartOfSpeech.NOUN for word_pair in result)


@pytest.mark.asyncio
async def test_adversarial_zero_limit_raises_value_error_when_context_injected(sampler: WordSampler) -> None:
    """With source-language context injected, a non-positive limit raises ValueError."""
    sampler._source_language = Language.NL
    patch_store(sampler, [make_scored_pair("huis", "dom")])

    with pytest.raises(ValueError, match="limit must be positive"):
        await sampler.sample_adversarial(make_word("kat"), 0)
