"""Prompt authoring helper — serialize ChatPromptTemplate to JSON.

Usage:
    1. Edit the `build_prompt()` function below to define your prompt.
    2. Set OUTPUT_PATH to your desired output file path.
    3. Run: uv run python nl_processing/core/scripts/prompt_author.py

The output JSON can be loaded by `nl_processing.core.prompts.load_prompt()`.
"""

import json

from langchain_core.prompts import ChatPromptTemplate


def build_prompt() -> ChatPromptTemplate:
    """Define your prompt here. Edit this function for each prompt you author."""
    return ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant. Respond in {language}."),
        ("human", "{input}"),
    ])


def serialize_prompt_to_json(prompt: ChatPromptTemplate, output_path: str) -> None:
    """Serialize a ChatPromptTemplate to JSON format compatible with load_prompt().

    Args:
        prompt: The ChatPromptTemplate to serialize.
        output_path: Path where to save the JSON file.
    """
    messages = []
    for msg in prompt.messages:
        if hasattr(msg, "prompt") and hasattr(msg.prompt, "template"):
            # Extract role from class name
            role_class = msg.__class__.__name__.replace("MessagePromptTemplate", "").lower()
            if role_class == "system":
                role = "system"
            elif role_class == "human":
                role = "human"
            elif role_class == "ai":
                role = "ai"
            else:
                # Fallback for any other role types
                role = "human"
            template = msg.prompt.template
            messages.append([role, template])

    data = {"messages": messages}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


OUTPUT_PATH = "output_prompt.json"


if __name__ == "__main__":
    prompt = build_prompt()
    serialize_prompt_to_json(prompt, OUTPUT_PATH)
    print(f"Prompt saved to {OUTPUT_PATH}")  # noqa: T201 — dev script, print is intentional
