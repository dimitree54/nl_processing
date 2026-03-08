import json
from pathlib import Path

from langchain_core.load import dumpd
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
import pytest

from nl_processing.core.prompts import load_prompt


def _write_prompt_json(path: Path, prompt: ChatPromptTemplate) -> Path:
    """Serialize a ChatPromptTemplate to a JSON file using LangChain native format."""
    data = dumpd(prompt)
    path.write_text(json.dumps(data))
    return path


def test_load_prompt_valid_file(tmp_path: Path) -> None:
    """Test loading a valid prompt JSON file."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant."),
        ("human", "{input}"),
    ])
    prompt_file = _write_prompt_json(tmp_path / "test_prompt.json", prompt)

    loaded = load_prompt(str(prompt_file))

    assert isinstance(loaded, ChatPromptTemplate)
    assert "input" in loaded.input_variables


def test_load_prompt_missing_file() -> None:
    """Test loading a non-existent prompt file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Prompt file not found"):
        load_prompt("nonexistent.json")


def test_load_prompt_malformed_json(tmp_path: Path) -> None:
    """Test loading malformed JSON raises ValueError."""
    prompt_file = tmp_path / "bad_prompt.json"
    prompt_file.write_text("{ invalid json")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_prompt(str(prompt_file))


def test_load_prompt_not_dict(tmp_path: Path) -> None:
    """Test loading non-dict JSON raises TypeError."""
    prompt_file = tmp_path / "not_dict.json"
    prompt_file.write_text('"just a string"')

    with pytest.raises(TypeError, match="must contain a JSON object"):
        load_prompt(str(prompt_file))


def test_load_prompt_non_langchain_dict(tmp_path: Path) -> None:
    """Test loading a dict that is not a LangChain serialization raises TypeError."""
    prompt_file = tmp_path / "not_langchain.json"
    prompt_file.write_text('{"other_field": "value"}')

    with pytest.raises(TypeError, match="Expected ChatPromptTemplate, got dict"):
        load_prompt(str(prompt_file))


def test_load_prompt_invalid_langchain_class(tmp_path: Path) -> None:
    """Test loading a LangChain dict with an unresolvable class raises ValueError."""
    invalid_data = {"lc": 1, "type": "constructor", "id": ["invalid", "module", "Klass"], "kwargs": {}}
    prompt_file = tmp_path / "bad_lc.json"
    prompt_file.write_text(json.dumps(invalid_data))

    with pytest.raises(ValueError, match="Failed to deserialize ChatPromptTemplate"):
        load_prompt(str(prompt_file))


def test_load_prompt_wrong_langchain_type(tmp_path: Path) -> None:
    """Test loading a valid LangChain object that is not ChatPromptTemplate raises TypeError."""
    pt = PromptTemplate.from_template("Hello {name}!")
    data = dumpd(pt)
    prompt_file = tmp_path / "not_chat.json"
    prompt_file.write_text(json.dumps(data))

    with pytest.raises(TypeError, match="Expected ChatPromptTemplate, got PromptTemplate"):
        load_prompt(str(prompt_file))


def test_load_prompt_round_trip(tmp_path: Path) -> None:
    """Test creating, saving, and loading a prompt preserves content."""
    original = ChatPromptTemplate.from_messages([
        ("system", "You are helpful."),
        ("human", "Hello {name}!"),
    ])
    prompt_file = _write_prompt_json(tmp_path / "roundtrip.json", original)

    loaded = load_prompt(str(prompt_file))

    assert loaded.input_variables == original.input_variables
    assert len(loaded.messages) == len(original.messages)

    test_input = {"name": "Alice"}
    original_formatted = original.format_messages(**test_input)
    loaded_formatted = loaded.format_messages(**test_input)

    assert len(original_formatted) == len(loaded_formatted)
    for orig_msg, loaded_msg in zip(original_formatted, loaded_formatted):
        assert orig_msg.content == loaded_msg.content


def test_load_prompt_empty_messages(tmp_path: Path) -> None:
    """Test loading prompt with empty messages list."""
    prompt = ChatPromptTemplate.from_messages([])
    prompt_file = _write_prompt_json(tmp_path / "empty.json", prompt)

    loaded = load_prompt(str(prompt_file))

    assert isinstance(loaded, ChatPromptTemplate)
    assert len(loaded.messages) == 0


def test_load_prompt_complex_template(tmp_path: Path) -> None:
    """Test loading prompt with multiple variables and complex templates."""
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a {role} assistant."),
        ("human", "Process this {data_type}: {content}"),
        ("ai", "I'll help you with that."),
        ("human", "Thanks! Please {action}."),
    ])
    prompt_file = _write_prompt_json(tmp_path / "complex.json", prompt)

    loaded = load_prompt(str(prompt_file))

    assert isinstance(loaded, ChatPromptTemplate)
    expected_vars = {"role", "data_type", "content", "action"}
    assert set(loaded.input_variables) == expected_vars
