from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text.service import TextTranslator
from tests.unit.translate_text.conftest import _AsyncChainMock, make_tool_response


def test_constructor_valid_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test TextTranslator constructor with NL->RU succeeds."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    assert translator._source_language == Language.NL
    assert translator._target_language == Language.RU
    assert translator._chain is not None


def test_constructor_unsupported_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test TextTranslator raises ValueError for unsupported pair RU->NL."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    with pytest.raises(ValueError, match="Unsupported language pair"):
        TextTranslator(source_language=Language.RU, target_language=Language.NL)


def test_constructor_custom_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test TextTranslator constructor accepts custom model parameter."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = TextTranslator(
        source_language=Language.NL,
        target_language=Language.RU,
        model="gpt-4o",
    )
    assert translator._chain is not None


@pytest.mark.asyncio
async def test_translate_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test translate returns translated text from mocked chain."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    expected_text = "Сегодня светит солнце."

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMock(make_tool_response(expected_text))

    result = await translator.translate("De zon schijnt vandaag.")
    assert result == expected_text


@pytest.mark.asyncio
async def test_translate_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test empty string input returns empty string without chain call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("should not be called"))
    translator._chain = mock_chain

    result = await translator.translate("")
    assert result == ""
    assert len(mock_chain.ainvoke_calls) == 0, "Chain should not be called for empty input"


@pytest.mark.asyncio
async def test_translate_whitespace_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test whitespace-only input returns empty string without chain call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("should not be called"))
    translator._chain = mock_chain

    result = await translator.translate("   \n  \t  ")
    assert result == ""
    assert len(mock_chain.ainvoke_calls) == 0, "Chain should not be called for whitespace input"


@pytest.mark.asyncio
async def test_translate_invokes_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that translate invokes ainvoke with correct structure."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = TextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_tool_response("Результат"))
    translator._chain = mock_chain

    await translator.translate("Tekst om te vertalen")

    assert len(mock_chain.ainvoke_calls) == 1
    call_args = mock_chain.ainvoke_calls[0]
    assert "text" in call_args
    assert len(call_args["text"]) == 1
