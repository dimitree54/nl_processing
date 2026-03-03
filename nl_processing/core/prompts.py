import json
from pathlib import Path

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate


def load_prompt(prompt_path: str) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a LangChain-serialized JSON file.

    The JSON file must contain the output of ``langchain_core.load.dumpd(prompt)``.

    Args:
        prompt_path: Path to the prompt JSON file in LangChain native format.

    Returns:
        A ChatPromptTemplate ready for chain composition.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError: If the JSON file is malformed or cannot be deserialized.
        TypeError: If the file content is not a JSON object or the deserialized
            object is not a ChatPromptTemplate.
    """
    path = Path(prompt_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in prompt file {prompt_path}: {e}") from e

    if not isinstance(data, dict):
        raise TypeError(f"Prompt file must contain a JSON object, got {type(data).__name__}")

    try:
        prompt = load(data)
    except Exception as e:
        raise ValueError(f"Failed to deserialize ChatPromptTemplate from {prompt_path}: {e}") from e

    if not isinstance(prompt, ChatPromptTemplate):
        raise TypeError(f"Expected ChatPromptTemplate, got {type(prompt).__name__} from {prompt_path}")

    return prompt
