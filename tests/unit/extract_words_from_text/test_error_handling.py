import pytest

from nl_processing.core.exceptions import APIError
from nl_processing.extract_words_from_text.service import WordExtractor
from tests.unit.extract_words_from_text.conftest import _AsyncChainMockError


@pytest.mark.asyncio
async def test_api_error_wrapping_runtime_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that RuntimeError from chain is wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    extractor = WordExtractor()
    extractor._chain = _AsyncChainMockError(RuntimeError("API failed"))

    with pytest.raises(APIError) as exc_info:
        await extractor.extract("De kat loopt.")

    assert exc_info.value.__cause__.__class__ == RuntimeError
    assert str(exc_info.value.__cause__) == "API failed"


@pytest.mark.asyncio
async def test_api_error_wrapping_various_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that various exceptions from chain are wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    exceptions_to_test = [
        ValueError("Value error"),
        ConnectionError("Connection failed"),
        KeyError("Key error"),
        Exception("Generic exception"),
    ]

    extractor = WordExtractor()

    for original_exception in exceptions_to_test:
        extractor._chain = _AsyncChainMockError(original_exception)

        with pytest.raises(APIError) as exc_info:
            await extractor.extract("De kat loopt.")

        assert exc_info.value.__cause__ is original_exception


@pytest.mark.asyncio
async def test_api_error_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that APIError preserves the original exception as __cause__."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    original = RuntimeError("upstream failure")

    extractor = WordExtractor()
    extractor._chain = _AsyncChainMockError(original)

    with pytest.raises(APIError) as exc_info:
        await extractor.extract("De kat loopt.")

    assert exc_info.value.__cause__ is original
    assert str(exc_info.value) == "upstream failure"
