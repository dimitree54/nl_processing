from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator
from tests.unit.translate_text_bidirectional.conftest import (
    _AsyncChainMock,
    make_nl_to_ru_response,
    make_ru_to_nl_response,
)


def test_constructor_valid_pair_nl_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    """NL, RU constructor order succeeds."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    assert translator._chain is not None


def test_constructor_valid_pair_ru_nl(monkeypatch: pytest.MonkeyPatch) -> None:
    """RU, NL constructor order succeeds (CR-1: unordered pair)."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.RU, target_language=Language.NL)
    assert translator._chain is not None


def test_constructor_unsupported_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unsupported pair raises ValueError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with pytest.raises(ValueError, match="Unsupported language pair"):
        BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.NL)


def test_constructor_custom_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom model and service_tier accepted."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(
        source_language=Language.NL,
        target_language=Language.RU,
        model="gpt-4o",
        service_tier="default",
    )
    assert translator._chain is not None


def test_constructor_uses_priority_tier_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default constructor should request the priority service tier."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    captured: dict[str, object] = {}

    def _fake_build(**kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "nl_processing.translate_text_bidirectional.service.build_bidirectional_translation_chain",
        _fake_build,
    )
    BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    assert captured["model"] == "gpt-4.1-mini"
    assert captured["service_tier"] == "priority"


@pytest.mark.asyncio
async def test_translate_nl_to_ru_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Dutch input returns Russian from NL→RU tool."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    expected = "Сегодня светит солнце."
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMock(make_nl_to_ru_response(expected))
    result = await translator.translate("De zon schijnt vandaag.")
    assert result == expected


@pytest.mark.asyncio
async def test_translate_ru_to_nl_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Russian input returns Dutch from RU→NL tool."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    expected = "De zon schijnt vandaag."
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMock(make_ru_to_nl_response(expected))
    result = await translator.translate("Сегодня светит солнце.")
    assert result == expected


@pytest.mark.asyncio
async def test_translate_empty_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty input returns empty string without chain call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_nl_to_ru_response("should not be called"))
    translator._chain = mock_chain
    result = await translator.translate("")
    assert result == ""
    assert len(mock_chain.ainvoke_calls) == 0


@pytest.mark.asyncio
async def test_translate_whitespace_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only input returns empty string without chain call."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_nl_to_ru_response("should not be called"))
    translator._chain = mock_chain
    result = await translator.translate("   \n  \t  ")
    assert result == ""
    assert len(mock_chain.ainvoke_calls) == 0


@pytest.mark.asyncio
async def test_translate_invokes_chain(monkeypatch: pytest.MonkeyPatch) -> None:
    """translate invokes ainvoke with correct structure."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    mock_chain = _AsyncChainMock(make_nl_to_ru_response("Результат"))
    translator._chain = mock_chain
    await translator.translate("Tekst om te vertalen")
    assert len(mock_chain.ainvoke_calls) == 1
    call_args = mock_chain.ainvoke_calls[0]
    assert "text" in call_args
    assert len(call_args["text"]) == 1
