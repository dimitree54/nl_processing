import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.translate_word.service import WordTranslator


@pytest.mark.asyncio
async def test_realistic_pipeline_input() -> None:
    """Translate a list of normalized Dutch words like output from extract_words_from_text."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [
        Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="mooi", word_type=PartOfSpeech.ADJECTIVE, language=Language.NL),
        Word(normalized_form="in", word_type=PartOfSpeech.PREPOSITION, language=Language.NL),
        Word(normalized_form="Nederland", word_type=PartOfSpeech.PROPER_NOUN_COUNTRY, language=Language.NL),
    ]
    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"
    for i, result in enumerate(results):
        assert isinstance(result, Word), f"Result #{i} is {type(result).__name__}, expected Word"
        assert result.normalized_form.strip(), (
            f"Result #{i} has empty normalized_form for word '{words[i].normalized_form}'"
        )


@pytest.mark.asyncio
async def test_one_to_one_mapping_verification() -> None:
    """Pass N words, verify exactly N results in the same order."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [
        Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"
    for i, result in enumerate(results):
        assert isinstance(result, Word), f"Result #{i} is {type(result).__name__}, expected Word"
        assert result.normalized_form.strip(), f"Result #{i} has empty normalized_form"


@pytest.mark.asyncio
async def test_empty_input_handling() -> None:
    """translate([]) returns []."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    results = await translator.translate([])
    assert results == []


def test_unsupported_pair_at_init() -> None:
    """WordTranslator with unsupported pair raises ValueError."""
    with pytest.raises(ValueError, match="Unsupported language pair"):
        WordTranslator(source_language=Language.RU, target_language=Language.NL)


@pytest.mark.asyncio
async def test_single_word_translation() -> None:
    """Translate a single word, verify output is a list with 1 Word."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    input_words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    results = await translator.translate(input_words)

    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    assert isinstance(results[0], Word)
    assert results[0].normalized_form.strip(), "Translation should not be empty"
    assert results[0].language == Language.RU
