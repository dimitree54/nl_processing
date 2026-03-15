from nl_processing.core.exceptions import APIError
from nl_processing.core.models import Language
import pytest

from nl_processing.extract_interesting_facts.service import InterestingFactsExtractor
from tests.unit.extract_interesting_facts.conftest import _AsyncChainMock, _AsyncChainMockError, _make_text_response


@pytest.mark.asyncio
async def test_blank_input_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty string raises ValueError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    with pytest.raises(ValueError, match="Input text must not be blank or whitespace-only"):
        await extractor.extract("")


@pytest.mark.asyncio
async def test_whitespace_input_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whitespace-only input raises ValueError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    with pytest.raises(ValueError, match="Input text must not be blank or whitespace-only"):
        await extractor.extract("   \n\t  ")


@pytest.mark.asyncio
async def test_chain_exception_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """RuntimeError from chain is wrapped as APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    original_error = RuntimeError("Chain failed")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    extractor._chain = _AsyncChainMockError(original_error)
    with pytest.raises(APIError, match="Chain failed"):
        await extractor.extract("test")


@pytest.mark.asyncio
async def test_api_error_preserves_cause(monkeypatch: pytest.MonkeyPatch) -> None:
    """Original exception is preserved as __cause__."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    original_error = RuntimeError("Chain failed")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    extractor._chain = _AsyncChainMockError(original_error)
    with pytest.raises(APIError) as exc_info:
        await extractor.extract("test")
    assert exc_info.value.__cause__ is original_error


@pytest.mark.asyncio
async def test_api_error_various_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Various exception types all become APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)

    # Test ValueError becomes APIError
    extractor._chain = _AsyncChainMockError(ValueError("Value error"))
    with pytest.raises(APIError, match="Value error"):
        await extractor.extract("test")

    # Test ConnectionError becomes APIError
    extractor._chain = _AsyncChainMockError(ConnectionError("Connection error"))
    with pytest.raises(APIError, match="Connection error"):
        await extractor.extract("test")

    # Test KeyError becomes APIError
    extractor._chain = _AsyncChainMockError(KeyError("Key error"))
    with pytest.raises(APIError, match="'Key error'"):
        await extractor.extract("test")


@pytest.mark.asyncio
async def test_empty_response_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty model response raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    extractor._chain = _AsyncChainMock(_make_text_response(""))
    with pytest.raises(APIError, match="Model returned empty response"):
        await extractor.extract("test")


@pytest.mark.asyncio
async def test_short_response_raises_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Very short model response raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extractor = InterestingFactsExtractor(source_language=Language.NL, target_language=Language.RU)
    extractor._chain = _AsyncChainMock(_make_text_response("abc"))
    with pytest.raises(APIError, match="Model returned unusably short response"):
        await extractor.extract("test")
