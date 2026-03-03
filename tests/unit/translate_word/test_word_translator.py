import pytest

from nl_processing.core.models import Language, TranslationResult
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
        {"translation": "дом"},
        {"translation": "ходить"},
        {"translation": "быстро"},
    ]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    results = await translator.translate(["huis", "lopen", "snel"])

    assert len(results) == 3
    assert results[0].translation == "дом"
    assert results[1].translation == "ходить"
    assert results[2].translation == "быстро"


@pytest.mark.asyncio
async def test_translate_one_to_one_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """len(output) == len(input) with mock."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    words = ["huis", "boek", "water", "zon", "brood"]
    mock_translations = [
        {"translation": "дом"},
        {"translation": "книга"},
        {"translation": "вода"},
        {"translation": "солнце"},
        {"translation": "хлеб"},
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
        {"translation": "кошка"},
        {"translation": "книга"},
    ]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    results = await translator.translate(["de kat", "het boek"])

    assert results[0].translation == "кошка"
    assert results[1].translation == "книга"


@pytest.mark.asyncio
async def test_translate_returns_translation_result_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Each item is a TranslationResult with a translation field."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    mock_translations = [{"translation": "дом"}]
    translator._chain = _AsyncChainMock(make_tool_response(mock_translations))

    results = await translator.translate(["huis"])

    assert len(results) == 1
    assert isinstance(results[0], TranslationResult)
    assert results[0].translation == "дом"
