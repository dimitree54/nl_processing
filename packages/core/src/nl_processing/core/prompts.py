import json
import pathlib
from typing import NotRequired, TypedDict

from langchain_core.load import load
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate


class ChatOpenAIKwargs(TypedDict):
    model: str
    service_tier: NotRequired[str]
    reasoning_effort: NotRequired[str]
    temperature: NotRequired[float]


def build_llm_kwargs(
    *,
    model: str,
    service_tier: str | None,
    reasoning_effort: str | None,
    temperature: float | None,
) -> ChatOpenAIKwargs:
    """Build ChatOpenAI kwargs without forwarding None-valued options."""
    kwargs: ChatOpenAIKwargs = {"model": model}
    if service_tier is not None:
        kwargs["service_tier"] = service_tier
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if temperature is not None:
        kwargs["temperature"] = temperature
    return kwargs


def load_prompt(prompt_path: str) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a LangChain-serialized JSON file.

    The JSON file must contain the output of ``langchain_core.load.dumpd(prompt)``.

    Args:
        prompt_path: Path to the prompt JSON file in LangChain native format.

    Returns:
        A ChatPromptTemplate ready for chain composition.
    """
    path = pathlib.Path(prompt_path)

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise TypeError(f"Prompt file must contain a JSON object, got {type(data).__name__}")

    prompt = load(data)

    if not isinstance(prompt, ChatPromptTemplate):
        raise TypeError(f"Expected ChatPromptTemplate, got {type(prompt).__name__} from {prompt_path}")

    return prompt


def build_tool_call_ai_message(
    tool_name: str,
    tool_args: dict[str, object],
    call_id: str,
    *,
    content: str = "",
) -> AIMessage:
    return AIMessage(
        content=content,
        tool_calls=[{"name": tool_name, "args": tool_args, "id": call_id}],
    )
