"""Integration tests for live word extraction with OpenAI API."""

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

from nl_processing.extract_word_details.service import WordDetailsExtractor


@pytest.mark.asyncio
async def test_live_extraction_noun() -> None:
    """Test live extraction for a Dutch noun with Russian explanations."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    words = [Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    results = await extractor.extract(words)

    assert len(results) == 1
    assert results[0].source_word == "hond"
    assert results[0].word_type == "noun"
    assert results[0].schema_key == "nl_ru_noun"
    assert results[0].schema_version == 1
    assert isinstance(results[0].payload, dict)


@pytest.mark.asyncio
async def test_live_extraction_verb() -> None:
    """Test live extraction for a Dutch verb with Russian explanations."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    words = [Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL)]
    results = await extractor.extract(words)

    assert len(results) == 1
    assert results[0].source_word == "lopen"
    assert results[0].word_type == "verb"
    assert results[0].schema_key == "nl_ru_verb"
    assert results[0].schema_version == 1
    assert isinstance(results[0].payload, dict)


@pytest.mark.asyncio
async def test_live_extraction_multiple_same_pos() -> None:
    """Test live extraction for multiple Dutch words of same POS."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    words = [
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="vogel", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    results = await extractor.extract(words)

    assert len(results) == 3
    assert all(result.word_type == "noun" for result in results)
    assert all(result.schema_key == "nl_ru_noun" for result in results)

    # Verify order preservation
    assert results[0].source_word == "hond"
    assert results[1].source_word == "kat"
    assert results[2].source_word == "vogel"


@pytest.mark.asyncio
async def test_live_extraction_order_preservation() -> None:
    """Test that original word order is preserved in results."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    words = [
        Word(normalized_form="groot", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="hond", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="snel", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
    ]
    results = await extractor.extract(words)

    assert len(results) == 4

    # Verify order is preserved
    assert results[0].source_word == "groot"
    assert results[0].word_type == "adjective"

    assert results[1].source_word == "hond"
    assert results[1].word_type == "noun"

    assert results[2].source_word == "lopen"
    assert results[2].word_type == "verb"

    assert results[3].source_word == "snel"
    assert results[3].word_type == "adjective"


@pytest.mark.asyncio
async def test_live_extraction_empty_input() -> None:
    """Test live extraction with empty word list."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    results = await extractor.extract([])
    assert results == []


@pytest.mark.asyncio
async def test_live_extraction_single_word() -> None:
    """Test live extraction with single word input."""
    extractor = WordDetailsExtractor(
        source_language=Language.NL,
        target_language=Language.RU,
    )

    words = [Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    results = await extractor.extract(words)

    assert len(results) == 1
    assert results[0].source_word == "water"
    assert results[0].word_type == "noun"
    assert results[0].schema_key == "nl_ru_noun"
