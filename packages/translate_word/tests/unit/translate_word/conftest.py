"""Test fixtures for translate_word unit tests."""

from tests.conftest import (
    AsyncChainMock as _AsyncChainMock,
    AsyncChainMockError as _AsyncChainMockError,
    make_tool_response as _make_response,
)

__all__ = ["_AsyncChainMock", "_AsyncChainMockError", "make_tool_response"]


def make_tool_response(translations: list[dict[str, str]]) -> object:
    """Build a fake LLM response with tool_calls for _TranslationBatch."""
    return _make_response({"translations": translations})
