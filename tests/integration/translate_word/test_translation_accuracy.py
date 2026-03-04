import time

import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.translate_word.service import WordTranslator

_QUALITY_TEST_CASES: list[tuple[Word, str]] = [
    (Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL), "дом"),
    (Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL), "книга"),
    (Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL), "вода"),
    (Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL), "солнце"),
    (Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL), "хлеб"),
    (Word(normalized_form="melk", word_type=PartOfSpeech.NOUN, language=Language.NL), "молоко"),
    (Word(normalized_form="school", word_type=PartOfSpeech.NOUN, language=Language.NL), "школа"),
    (Word(normalized_form="tafel", word_type=PartOfSpeech.NOUN, language=Language.NL), "стол"),
    (Word(normalized_form="stoel", word_type=PartOfSpeech.NOUN, language=Language.NL), "стул"),
    (Word(normalized_form="deur", word_type=PartOfSpeech.NOUN, language=Language.NL), "дверь"),
]


@pytest.mark.asyncio
async def test_translation_quality_10_words() -> None:
    """10 unambiguous Dutch words with 100% exact match (TW-FR10)."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [word for word, _ in _QUALITY_TEST_CASES]
    expected = [translation for _, translation in _QUALITY_TEST_CASES]

    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"

    for i, (result, expected_translation) in enumerate(zip(results, expected)):
        assert result.normalized_form == expected_translation, (
            f"Word #{i} '{words[i].normalized_form}': expected '{expected_translation}', got '{result.normalized_form}'"
        )


@pytest.mark.asyncio
async def test_one_to_one_mapping_5_words() -> None:
    """5 words produce exactly 5 Word objects in order."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [
        Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    results = await translator.translate(words)

    assert len(results) == 5, f"Expected 5 results, got {len(results)}"
    for i, result in enumerate(results):
        assert isinstance(result, Word), f"Result #{i} is {type(result).__name__}, expected Word"
        assert result.normalized_form.strip(), f"Result #{i} has empty normalized_form"


@pytest.mark.asyncio
async def test_translation_performance_10_words() -> None:
    """10 words translate in <10 seconds (relaxed from <1s PRD target due to network latency + retries)."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [word for word, _ in _QUALITY_TEST_CASES]

    start = time.time()
    await translator.translate(words)
    elapsed = time.time() - start

    assert elapsed < 10, f"Translation took {elapsed:.2f}s -- exceeds 10.00s QA gate"


@pytest.mark.asyncio
async def test_empty_input_returns_empty_list() -> None:
    """Empty input returns empty list without API call."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    start = time.time()
    results = await translator.translate([])
    elapsed = time.time() - start

    assert results == []
    assert elapsed < 0.01, f"Empty input took {elapsed:.2f}s -- should be near-instant"
