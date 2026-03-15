"""Shared test helpers for async chain mocking."""

from types import SimpleNamespace


class AsyncChainMock:
    """Async mock for a LangChain chain returning plain-text content."""

    def __init__(self, return_value: SimpleNamespace) -> None:
        self.ainvoke_calls: list[dict[str, list[object]]] = []
        self._return_value = return_value

    async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
        self.ainvoke_calls.append(input_dict)
        return self._return_value


class AsyncChainMockError:
    """Async mock that raises on ainvoke."""

    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    async def ainvoke(self, _input_dict: dict[str, list[object]]) -> SimpleNamespace:
        raise self._exception


def make_text_response(content: str) -> SimpleNamespace:
    """Build a fake LLM response with plain .content (no tool_calls)."""
    resp = SimpleNamespace()
    resp.content = content
    return resp
