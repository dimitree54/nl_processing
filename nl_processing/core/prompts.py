import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate


def load_prompt(prompt_path: str) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a JSON file.

    Args:
        prompt_path: Path to the prompt JSON file in a simple format:
                     {"messages": [["role", "template"], ...]}

    Returns:
        A ChatPromptTemplate ready for chain composition.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
        ValueError: If the JSON file is malformed.
        TypeError: If the loaded data is not a valid prompt structure.
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

    if "messages" not in data:
        raise TypeError(f"Prompt file missing required 'messages' field")

    if not isinstance(data["messages"], list):
        raise TypeError(f"'messages' field must be a list, got {type(data['messages']).__name__}")

    try:
        # Convert list messages to tuples for ChatPromptTemplate
        messages = [tuple(msg) if isinstance(msg, list) else msg for msg in data["messages"]]
        return ChatPromptTemplate.from_messages(messages)
    except Exception as e:
        raise ValueError(f"Failed to create ChatPromptTemplate from messages: {e}") from e
