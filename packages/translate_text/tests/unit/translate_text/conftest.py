"""Test fixtures for translate_text unit tests."""

from tests.conftest import (
    AsyncChainMock as _AsyncChainMock,
    AsyncChainMockError as _AsyncChainMockError,
    make_tool_response as _make_response,
)

__all__ = ["_AsyncChainMock", "_AsyncChainMockError", "make_tool_response"]


def make_tool_response(text: str) -> object:
    """Build a fake LLM response with tool_calls for _TranslatedText."""
    return _make_response({"text": text})
