import json
import pathlib

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from nl_processing.core.models import Language


def build_translation_chain(
    *,
    source_language: Language,
    target_language: Language,
    prompts_dir: pathlib.Path,
    tool_schema: type[BaseModel],
    model: str,
    reasoning_effort: str | None = None,
    service_tier: str | None = None,
    temperature: float | None = 0,
) -> RunnableSerializable:  # type: ignore[type-arg]
    """Load a pair-specific prompt and return a prompt|llm chain.

    This is shared infrastructure for translation-style services that follow the
    pattern: resolve prompt file → load JSON prompt → bind_tools → compose chain.

    Args:
        source_language: Source language enum value used in the prompt filename.
        target_language: Target language enum value used in the prompt filename.
        prompts_dir: Directory containing ``<src>_<tgt>.json`` prompt files.
        tool_schema: Pydantic model class to bind as a tool.
        model: OpenAI model identifier string.
        reasoning_effort: Optional reasoning effort level for the model.
        service_tier: Optional service tier for the OpenAI API.
        temperature: LLM temperature (default 0 for deterministic output).

    Returns:
        A ``prompt | llm`` RunnableSerializable ready for ``ainvoke()``.
    """
    prompt_file = f"{source_language.value}_{target_language.value}.json"
    prompt = load_prompt(str(prompts_dir / prompt_file))

    llm = ChatOpenAI(
        model=model,
        temperature=temperature,
        reasoning_effort=reasoning_effort,
        service_tier=service_tier,
    ).bind_tools(
        [tool_schema],
        tool_choice=tool_schema.__name__,
    )
    return prompt | llm


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
