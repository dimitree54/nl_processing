import json
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
import pytest

from nl_processing.core.prompts import load_prompt


def test_load_prompt_valid_file(tmp_path: Path) -> None:
    """Test loading a valid prompt JSON file."""
    # Create a test prompt file
    prompt_data = {"messages": [["system", "You are a helpful assistant."], ["human", "{input}"]]}
    prompt_file = tmp_path / "test_prompt.json"
    prompt_file.write_text(json.dumps(prompt_data))

    # Load the prompt
    loaded = load_prompt(str(prompt_file))

    # Verify it's a ChatPromptTemplate
    assert isinstance(loaded, ChatPromptTemplate)

    # Verify input variables
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


def test_load_prompt_missing_messages_field(tmp_path: Path) -> None:
    """Test loading JSON without messages field raises TypeError."""
    prompt_file = tmp_path / "no_messages.json"
    prompt_file.write_text('{"other_field": "value"}')

    with pytest.raises(TypeError, match="missing required 'messages' field"):
        load_prompt(str(prompt_file))


def test_load_prompt_messages_not_list(tmp_path: Path) -> None:
    """Test loading JSON with non-list messages field raises TypeError."""
    prompt_file = tmp_path / "bad_messages.json"
    prompt_file.write_text('{"messages": "not a list"}')

    with pytest.raises(TypeError, match="'messages' field must be a list"):
        load_prompt(str(prompt_file))


def test_load_prompt_invalid_message_format(tmp_path: Path) -> None:
    """Test loading JSON with invalid message format raises ValueError."""
    prompt_file = tmp_path / "bad_format.json"
    prompt_file.write_text('{"messages": [["invalid_role", "template"]]}')

    with pytest.raises(ValueError, match="Failed to create ChatPromptTemplate"):
        load_prompt(str(prompt_file))


def test_load_prompt_round_trip(tmp_path: Path) -> None:
    """Test creating, saving, and loading a prompt preserves content."""
    # Create original prompt
    original = ChatPromptTemplate.from_messages([("system", "You are helpful."), ("human", "Hello {name}!")])

    # Save to JSON in our format
    prompt_data = {"messages": [["system", "You are helpful."], ["human", "Hello {name}!"]]}
    prompt_file = tmp_path / "roundtrip.json"
    prompt_file.write_text(json.dumps(prompt_data))

    # Load back
    loaded = load_prompt(str(prompt_file))

    # Compare key properties
    assert loaded.input_variables == original.input_variables
    assert len(loaded.messages) == len(original.messages)

    # Test that they produce the same formatted output
    test_input = {"name": "Alice"}
    original_formatted = original.format_messages(**test_input)
    loaded_formatted = loaded.format_messages(**test_input)

    assert len(original_formatted) == len(loaded_formatted)
    for orig, load in zip(original_formatted, loaded_formatted):
        assert orig.content == load.content


def test_load_prompt_empty_messages(tmp_path: Path) -> None:
    """Test loading prompt with empty messages list."""
    prompt_data = {"messages": []}
    prompt_file = tmp_path / "empty.json"
    prompt_file.write_text(json.dumps(prompt_data))

    loaded = load_prompt(str(prompt_file))
    assert isinstance(loaded, ChatPromptTemplate)
    assert len(loaded.messages) == 0


def test_load_prompt_complex_template(tmp_path: Path) -> None:
    """Test loading prompt with multiple variables and complex templates."""
    prompt_data = {
        "messages": [
            ["system", "You are a {role} assistant."],
            ["human", "Process this {data_type}: {content}"],
            ["ai", "I'll help you with that."],
            ["human", "Thanks! Please {action}."],
        ]
    }
    prompt_file = tmp_path / "complex.json"
    prompt_file.write_text(json.dumps(prompt_data))

    loaded = load_prompt(str(prompt_file))
    assert isinstance(loaded, ChatPromptTemplate)

    # Check all variables are detected
    expected_vars = {"role", "data_type", "content", "action"}
    assert set(loaded.input_variables) == expected_vars
