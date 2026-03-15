import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
import pytest

from nl_processing.core.prompts import load_prompt
from nl_processing.core.scripts.prompt_author import save_prompt, serialize_prompt_to_json


def test_serialize_prompt_to_json_writes_loadable_prompt(tmp_path: Path) -> None:
    """Test serialize_prompt_to_json writes LangChain JSON consumable by load_prompt."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Translate to {language}."),
        ("human", "{input}"),
    ])
    output_path = tmp_path / "prompt.json"

    serialize_prompt_to_json(prompt, str(output_path))

    data = json.loads(output_path.read_text(encoding="utf-8"))
    loaded_prompt = load_prompt(str(output_path))

    assert isinstance(data, dict)
    assert output_path.read_text(encoding="utf-8").endswith("\n")
    assert loaded_prompt.input_variables == prompt.input_variables
    loaded_messages = loaded_prompt.format_messages(language="Dutch", input="Hallo")
    expected_messages = prompt.format_messages(language="Dutch", input="Hallo")

    assert [message.content for message in loaded_messages] == [message.content for message in expected_messages]


def test_save_prompt_writes_prompt_and_prints_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test save_prompt writes a loadable prompt file and prints the expected summary."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "{input}"),
    ])
    output_path = tmp_path / "saved_prompt.json"

    save_prompt(prompt, str(output_path))

    captured = capsys.readouterr()
    loaded_prompt = load_prompt(str(output_path))
    loaded_messages = loaded_prompt.format_messages(input="Hello")
    expected_messages = prompt.format_messages(input="Hello")

    assert f"Prompt saved to {output_path}" in captured.out
    assert "Messages: 2" in captured.out
    assert "Input variables: ['input']" in captured.out
    assert [message.content for message in loaded_messages] == [message.content for message in expected_messages]
