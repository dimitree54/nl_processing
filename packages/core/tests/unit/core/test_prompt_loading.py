import json
from pathlib import Path

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate
import pytest

from nl_processing.core.prompts import load_prompt


def _write_prompt_json(path: Path, prompt: ChatPromptTemplate) -> Path:
    """Serialize a ChatPromptTemplate to a JSON file using LangChain native format."""
    data = dumpd(prompt)
    path.write_text(json.dumps(data))
    return path


def test_load_prompt_returns_stripped_content(tmp_path: Path) -> None:
    """Test load_prompt returns a valid ChatPromptTemplate from an existing file."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Translate the following text."),
        ("human", "{input}"),
    ])
    prompt_file = _write_prompt_json(tmp_path / "prompt.json", prompt)

    loaded = load_prompt(str(prompt_file))

    assert isinstance(loaded, ChatPromptTemplate)
    assert "input" in loaded.input_variables
    assert len(loaded.messages) == 2


def test_load_prompt_missing_file_raises_file_not_found_error() -> None:
    """Test load_prompt raises FileNotFoundError when prompt file does not exist."""
    with pytest.raises(FileNotFoundError, match="Prompt file not found"):
        load_prompt("/nonexistent/path/missing_prompt.json")
