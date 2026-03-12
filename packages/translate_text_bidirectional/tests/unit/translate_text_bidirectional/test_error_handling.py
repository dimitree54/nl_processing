from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
import pytest

from nl_processing.translate_text_bidirectional.service import BidirectionalTextTranslator
from tests.unit.translate_text_bidirectional.conftest import _AsyncChainMockError


@pytest.mark.asyncio
async def test_api_error_wrapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """RuntimeError from bidirectional translation chain is wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(RuntimeError("API failed"))
    with pytest.raises(APIError) as exc_info:
        await translator.translate("Hallo, dit is een test bericht.")
    assert exc_info.value.__cause__.__class__ == RuntimeError
    assert str(exc_info.value.__cause__) == "API failed"


@pytest.mark.asyncio
async def test_api_error_various_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Various exception types from bidirectional translation chain are wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    test_exceptions = [
        ValueError("Value error in bidirectional translation"),
        ConnectionError("Connection failed during translation"),
        KeyError("Key error in translation process"),
        Exception("Generic exception in bidirectional service"),
    ]
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    for original_exception in test_exceptions:
        translator._chain = _AsyncChainMockError(original_exception)
        with pytest.raises(APIError) as exc_info:
            await translator.translate("Bidirectionale vertaling test tekst")
        assert exc_info.value.__cause__ is original_exception


@pytest.mark.asyncio
async def test_api_error_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """APIError in bidirectional translator preserves the original exception as __cause__."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    original = ConnectionError("Network timeout")
    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(original)
    with pytest.raises(APIError) as exc_info:
        await translator.translate("Bidirectionele test boodschap")
    assert exc_info.value.__cause__ is original
    assert str(exc_info.value) == "Network timeout"
