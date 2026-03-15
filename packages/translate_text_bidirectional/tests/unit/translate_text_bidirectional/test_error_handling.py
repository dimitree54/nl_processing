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


@pytest.mark.asyncio
async def test_malformed_response_missing_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Response missing tool_calls attribute raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class MockResponseNoToolCalls:
        pass

    class MockChain:
        async def ainvoke(self, _: object) -> MockResponseNoToolCalls:  # noqa: ARG002
            return MockResponseNoToolCalls()

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = MockChain()

    with pytest.raises(APIError, match="LLM response missing tool_calls attribute"):
        await translator.translate("test text")


@pytest.mark.asyncio
async def test_malformed_response_empty_tool_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    """Response with empty tool_calls list raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class MockResponseEmptyToolCalls:
        tool_calls = []

    class MockChain:
        async def ainvoke(self, _: object) -> MockResponseEmptyToolCalls:  # noqa: ARG002
            return MockResponseEmptyToolCalls()

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = MockChain()

    with pytest.raises(APIError, match="LLM response contains no tool calls"):
        await translator.translate("test text")


@pytest.mark.asyncio
async def test_malformed_response_missing_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool call missing args field raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class MockResponseMissingArgs:
        tool_calls = [{"name": "some_tool"}]  # Missing args

    class MockChain:
        async def ainvoke(self, _: object) -> MockResponseMissingArgs:  # noqa: ARG002
            return MockResponseMissingArgs()

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = MockChain()

    with pytest.raises(APIError, match="Tool call missing 'args' field"):
        await translator.translate("test text")


@pytest.mark.asyncio
async def test_malformed_response_missing_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool call args missing text field raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class MockResponseMissingText:
        tool_calls = [{"name": "some_tool", "args": {"other_field": "value"}}]  # Missing text

    class MockChain:
        async def ainvoke(self, _: object) -> MockResponseMissingText:  # noqa: ARG002
            return MockResponseMissingText()

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = MockChain()

    with pytest.raises(APIError, match="Tool call args missing 'text' field"):
        await translator.translate("test text")


@pytest.mark.asyncio
async def test_malformed_response_non_string_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool call args.text that is not a string raises APIError."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class MockResponseNonStringText:
        tool_calls = [{"name": "some_tool", "args": {"text": 123}}]  # Non-string text

    class MockChain:
        async def ainvoke(self, _: object) -> MockResponseNonStringText:  # noqa: ARG002
            return MockResponseNonStringText()

    translator = BidirectionalTextTranslator(source_language=Language.NL, target_language=Language.RU)
    translator._chain = MockChain()

    with pytest.raises(APIError, match="Tool call args.text is not a string"):
        await translator.translate("test text")
