from types import SimpleNamespace


class _AsyncChainMock:
    """Async mock for the LangChain chain -- replaces unittest.mock.AsyncMock."""

    def __init__(self, return_value: SimpleNamespace) -> None:
        self.ainvoke_calls: list[dict[str, list[object]]] = []
        self._return_value = return_value

    async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
        self.ainvoke_calls.append(input_dict)
        return self._return_value


class _AsyncChainMockError:
    """Async mock that raises an exception on ainvoke."""

    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    async def ainvoke(self, _input_dict: dict[str, list[object]]) -> SimpleNamespace:
        raise self._exception


def make_tool_response(words: list[dict[str, str]]) -> SimpleNamespace:
    """Build a fake LLM response with tool_calls matching bind_tools output."""
    resp = SimpleNamespace()
    resp.tool_calls = [{"args": {"words": words}}]
    return resp
