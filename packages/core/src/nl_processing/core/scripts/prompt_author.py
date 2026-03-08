"""Prompt authoring helper — serialize ChatPromptTemplate to JSON.

Usage:
    1. Edit the ``build_prompt()`` function below to define your prompt.
    2. Set OUTPUT_PATH to your desired output file path.
    3. Run: uv run python src/nl_processing/core/scripts/prompt_author.py

The output JSON can be loaded by ``nl_processing.core.prompts.load_prompt()``.
"""

import json

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate


def build_prompt() -> ChatPromptTemplate:
    """Define your prompt here. Edit this function for each prompt you author."""
    return ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Respond in {language}."),
        ("human", "{input}"),
    ])


def serialize_prompt_to_json(prompt: ChatPromptTemplate, output_path: str) -> None:
    """Serialize a ChatPromptTemplate to JSON using LangChain native format.

    Args:
        prompt: The ChatPromptTemplate to serialize.
        output_path: Path where to save the JSON file.
    """
    data = dumpd(prompt)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def save_prompt(prompt: ChatPromptTemplate, output_path: str) -> None:
    """Serialize a prompt to JSON and print a summary to stdout.

    Intended for use in ``if __name__ == "__main__"`` blocks of prompt
    generation scripts so each script stays DRY.

    Args:
        prompt: The ChatPromptTemplate to serialize.
        output_path: Path where to save the JSON file.
    """
    serialize_prompt_to_json(prompt, output_path)
    print(f"Prompt saved to {output_path}")  # noqa: T201
    print(f"Messages: {len(prompt.messages)}")  # noqa: T201
    print(f"Input variables: {prompt.input_variables}")  # noqa: T201


OUTPUT_PATH = "output_prompt.json"


if __name__ == "__main__":
    _prompt = build_prompt()
    save_prompt(_prompt, OUTPUT_PATH)
