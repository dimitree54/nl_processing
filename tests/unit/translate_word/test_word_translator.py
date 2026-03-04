import pytest

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.translate_word.service import WordTranslator
from tests.unit.translate_word.conftest import _AsyncChainMock, make_tool_response


def test_constructor_valid_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """NL->RU pair is accepted without error."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
    assert translator._source_language == Language.NL
    assert translator._target_language == Language.RU
    assert translator._chain is not None


def test_constructor_unsupported_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU->NL pair raises ValueError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(ValueError, match="Unsupported language pair"):
        WordTranslator(source_language=Language.RU, target_language=Language.NL)


def test_constructor_custom_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom model parameter is accepted."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU, model="gpt-4.1")
    assert translator._chain is not None


@pytest.mark.asyncio
async def test_translate_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock returns 3 translations for 3 words."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    mock_translations = [
        {"normalized_form": "дом", "word_type": "noun"},
        {"normalized_form": "ходить", "word_type": "verb"},
        {"normalized_form": "быстро", "word_type": "adverb"},
    ]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    input_words = [
        Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
        Word(normalized_form="snel", word_type=PartOfSpeech.ADVERB, language=Language.NL),
    ]
    results = await translator.translate(input_words)

    assert len(results) == 3
    assert results[0].normalized_form == "дом"
    assert results[0].word_type == PartOfSpeech.NOUN
    assert results[0].language == Language.RU
    assert results[1].normalized_form == "ходить"
    assert results[1].word_type == PartOfSpeech.VERB
    assert results[1].language == Language.RU
    assert results[2].normalized_form == "быстро"
    assert results[2].word_type == PartOfSpeech.ADVERB
    assert results[2].language == Language.RU


@pytest.mark.asyncio
async def test_translate_one_to_one_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """len(output) == len(input) with mock."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = [
        Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="water", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="zon", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="brood", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    mock_translations = [
        {"normalized_form": "дом", "word_type": "noun"},
        {"normalized_form": "книга", "word_type": "noun"},
        {"normalized_form": "вода", "word_type": "noun"},
        {"normalized_form": "солнце", "word_type": "noun"},
        {"normalized_form": "хлеб", "word_type": "noun"},
    ]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    results = await translator.translate(words)

    assert len(results) == len(words), f"Expected {len(words)} results, got {len(results)}"


@pytest.mark.asyncio
async def test_translate_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty list returns empty list with zero chain calls."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    mock = _AsyncChainMock(make_tool_response([]))
    translator._chain = mock

    results = await translator.translate([])

    assert results == []
    assert len(mock.ainvoke_calls) == 0, "Chain should not be called for empty input"


@pytest.mark.asyncio
async def test_translate_preserves_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Translations match input word order."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    mock_translations = [
        {"normalized_form": "кошка", "word_type": "noun"},
        {"normalized_form": "книга", "word_type": "noun"},
    ]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    input_words = [
        Word(normalized_form="de kat", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="het boek", word_type=PartOfSpeech.NOUN, language=Language.NL),
    ]
    results = await translator.translate(input_words)

    assert results[0].normalized_form == "кошка"
    assert results[1].normalized_form == "книга"


@pytest.mark.asyncio
async def test_translate_returns_word_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each item is a Word with normalized_form, word_type, and language fields."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    mock_translations = [{"normalized_form": "дом", "word_type": "noun"}]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    input_words = [Word(normalized_form="huis", word_type=PartOfSpeech.NOUN, language=Language.NL)]
    results = await translator.translate(input_words)

    assert len(results) == 1
    assert isinstance(results[0], Word)
    assert results[0].normalized_form == "дом"
    assert results[0].word_type == PartOfSpeech.NOUN
    assert results[0].language == Language.RU
