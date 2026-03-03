import pytest

from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
from nl_processing.translate_word.service import WordTranslator
from tests.unit.translate_word.conftest import _AsyncChainMockError


@pytest.mark.asyncio
async def test_api_error_wrapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """RuntimeError from chain is wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(RuntimeError("API failed"))

    with pytest.raises(APIError) as exc_info:
        await translator.translate(["huis"])

    assert exc_info.value.__cause__.__class__ == RuntimeError
    assert str(exc_info.value.__cause__) == "API failed"


@pytest.mark.asyncio
async def test_api_error_various_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Multiple exception types are wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    exceptions_to_test = [
        ValueError("Value error"),
        ConnectionError("Connection failed"),
        KeyError("Key error"),
        Exception("Generic exception"),
    ]

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)

    for original_exception in exceptions_to_test:
        translator._chain = _AsyncChainMockError(original_exception)

        with pytest.raises(APIError) as exc_info:
            await translator.translate(["huis"])

        assert exc_info.value.__cause__ is original_exception


@pytest.mark.asyncio
async def test_api_error_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """__cause__ is preserved on the APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    original = RuntimeError("original cause")

    translator = WordTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = _AsyncChainMockError(original)

    with pytest.raises(APIError) as exc_info:
        await translator.translate(["boek"])

    assert exc_info.value.__cause__ is original
    assert str(exc_info.value) == "original cause"
