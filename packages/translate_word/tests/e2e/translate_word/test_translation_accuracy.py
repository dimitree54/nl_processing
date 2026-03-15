import time

from nl_processing.core.models import Language, PartOfSpeech, Word
import pytest

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
async def test_translation_quality_batch_and_performance() -> None:
    """One live batch should cover exact translations, one-to-one mapping, output contract, and latency."""
    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [word for word, _ in _QUALITY_TEST_CASES]
    expected = [translation for _, translation in _QUALITY_TEST_CASES]

    start = time.perf_counter()
    results = await translator.translate(words)
    elapsed = time.perf_counter() - start

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"
    assert elapsed < 20, f"Translation took {elapsed:.2f}s -- exceeds 20.00s QA gate"

    for index, (result, expected_translation) in enumerate(zip(results, expected)):
        assert isinstance(result, Word), f"Result #{index} is {type(result).__name__}, expected Word"
        assert result.language == Language.RU, f"Result #{index} has wrong language: {result.language.value}"
        assert result.normalized_form == expected_translation, (
            f"Word #{index} '{words[index].normalized_form}': expected '{expected_translation}', "
            f"got '{result.normalized_form}'"
        )
