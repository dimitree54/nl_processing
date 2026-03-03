"""Test fixtures for extract_words_from_text unit tests."""

from tests.conftest import (
    AsyncChainMock as _AsyncChainMock,
    AsyncChainMockError as _AsyncChainMockError,
    make_tool_response as _make_response,
)

__all__ = ["_AsyncChainMock", "_AsyncChainMockError", "make_tool_response"]


def make_tool_response(words: list[dict[str, str]]) -> object:
    """Build a fake LLM response with tool_calls for _WordList."""
    return _make_response({"words": words})
