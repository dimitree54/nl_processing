"""Unit tests for prompt consistency with POS model schemas."""

import json
from pathlib import Path

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import pytest


def load_prompt(prompt_path: str | Path) -> ChatPromptTemplate:
    """Load a ChatPromptTemplate from a LangChain-serialized JSON file.

    Replicate core.prompts.load_prompt functionality without cross-package import.
    """
    path = Path(prompt_path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return load(data)


class TestPromptSchemaConsistency:
    """Tests to verify prompt structure is consistent with schema requirements."""

    @pytest.fixture
    def prompts_dir(self) -> Path:
        """Path to the prompts directory."""
        return Path(__file__).parents[3] / "src" / "nl_processing" / "extract_word_details" / "prompts"

    POS_FILES = [
        "nl_ru_noun.json",
        "nl_ru_verb.json",
        "nl_ru_adjective.json",
        "nl_ru_adverb.json",
        "nl_ru_preposition.json",
        "nl_ru_conjunction.json",
        "nl_ru_pronoun.json",
        "nl_ru_article.json",
        "nl_ru_numeral.json",
        "nl_ru_interjection.json",
        "nl_ru_proper_noun_person.json",
        "nl_ru_proper_noun_country.json",
        "nl_ru_phrase.json",
    ]

    @pytest.mark.parametrize("pos_file", POS_FILES)
    def test_prompt_contains_text_placeholder(self, prompts_dir: Path, pos_file: str) -> None:
        """Test that each prompt contains a MessagesPlaceholder for 'text'."""
        filepath = prompts_dir / pos_file
        loaded = load_prompt(str(filepath))

        assert isinstance(loaded, ChatPromptTemplate), f"Prompt {pos_file} not a ChatPromptTemplate"
        assert "text" in loaded.input_variables, f"Prompt {pos_file} missing 'text' input variable"

        # Check that there's a MessagesPlaceholder with variable_name='text'
        text_placeholder_found = any(
            isinstance(message, MessagesPlaceholder) and message.variable_name == "text" for message in loaded.messages
        )
        assert text_placeholder_found, f"Prompt {pos_file} missing MessagesPlaceholder for 'text'"

    @pytest.mark.parametrize("pos_file", POS_FILES)
    def test_prompt_has_system_message(self, prompts_dir: Path, pos_file: str) -> None:
        """Test that each prompt has a system message with Russian instructions."""
        filepath = prompts_dir / pos_file
        loaded = load_prompt(str(filepath))

        assert isinstance(loaded, ChatPromptTemplate)
        assert len(loaded.messages) > 0, f"Prompt {pos_file} has no messages"

        first_message = loaded.messages[0]

        # Check that the content contains Russian text (Cyrillic characters)
        try:
            content = str(first_message.content)
            assert any(ord(char) >= 0x0400 and ord(char) <= 0x04FF for char in content), (
                f"System message in {pos_file} does not contain Russian (Cyrillic) text"
            )
        except (AttributeError, TypeError):
            pytest.fail(f"First message in {pos_file} has no accessible content")

    @pytest.mark.parametrize("pos_file", POS_FILES)
    def test_prompt_has_few_shot_examples(self, prompts_dir: Path, pos_file: str) -> None:
        """Test that each prompt has few-shot examples with tool calls."""
        filepath = prompts_dir / pos_file
        loaded = load_prompt(str(filepath))

        assert isinstance(loaded, ChatPromptTemplate)
        assert len(loaded.messages) >= 5, f"Prompt {pos_file} should have at least 5 messages"

        # Look for AIMessage with tool_calls
        ai_message_with_tools_found = False
        for message in loaded.messages:
            try:
                if message.tool_calls:
                    ai_message_with_tools_found = True
                    break
            except AttributeError:
                continue
        assert ai_message_with_tools_found, f"Prompt {pos_file} missing AIMessage with tool calls"
