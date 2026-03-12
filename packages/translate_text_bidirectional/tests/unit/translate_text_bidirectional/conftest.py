"""Test fixtures for translate_text_bidirectional unit tests."""

from tests.conftest import (
    AsyncChainMock as _AsyncChainMock,
    AsyncChainMockError as _AsyncChainMockError,
    make_tool_response as _make_response,
)

__all__ = [
    "_AsyncChainMock",
    "_AsyncChainMockError",
    "make_nl_to_ru_response",
    "make_ru_to_nl_response",
]


def make_nl_to_ru_response(text: str) -> object:
    """Build a fake LLM response with _NlToRuTranslation tool call."""
    return _make_response({"text": text}, "_NlToRuTranslation")


def make_ru_to_nl_response(text: str) -> object:
    """Build a fake LLM response with _RuToNlTranslation tool call."""
    return _make_response({"text": text}, "_RuToNlTranslation")
