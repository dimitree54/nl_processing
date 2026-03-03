import pytest

from nl_processing.core.models import Language, TranslationResult
from nl_processing.translate_word.service import WordTranslator


@pytest.mark.asyncio
async def test_realistic_pipeline_input() -> None:
    """Translate a list of normalized Dutch words like output from extract_words_from_text."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = ["de kat", "lopen", "mooi", "in", "Nederland"]
    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"
    for i, result in enumerate(results):
        assert isinstance(result, TranslationResult), (
            f"Result #{i} is {type(result).__name__}, expected TranslationResult"
        )
        assert result.translation.strip(), f"Result #{i} has empty translation for word '{words[i]}'"


@pytest.mark.asyncio
async def test_one_to_one_mapping_verification() -> None:
    """Pass N words, verify exactly N results in the same order."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = ["huis", "boek", "water"]
    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"
    for i, result in enumerate(results):
        assert isinstance(result, TranslationResult), (
            f"Result #{i} is {type(result).__name__}, expected TranslationResult"
        )
        assert result.translation.strip(), f"Result #{i} has empty translation"


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
    """Translate a single word, verify output is a list with 1 TranslationResult."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    results = await translator.translate(["huis"])

    assert len(results) == 1, f"Expected 1 result, got {len(results)}"
    assert isinstance(results[0], TranslationResult)
    assert results[0].translation.strip(), "Translation should not be empty"
