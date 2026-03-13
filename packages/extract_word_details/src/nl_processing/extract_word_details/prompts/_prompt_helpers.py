"""Shared helpers for prompt generation scripts."""

from langchain_core.messages import AIMessage


def make_example_ai(details: list[dict], call_id: str, batch_name: str) -> AIMessage:
    """Create an AIMessage with a tool_call for the batch model."""
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": batch_name,
                "args": {"details": details},
                "id": call_id,
            }
        ],
    )
