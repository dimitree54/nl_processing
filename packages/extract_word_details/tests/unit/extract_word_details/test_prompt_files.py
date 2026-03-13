"""Unit tests for prompt file existence and basic validation."""

import json
from pathlib import Path

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate
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


class TestPromptFiles:
    """Tests for prompt file existence and basic JSON validation."""

    @pytest.fixture
    def prompts_dir(self) -> Path:
        """Path to the prompts directory."""
        return Path(__file__).parents[3] / "src" / "nl_processing" / "extract_word_details" / "prompts"

    def test_all_13_prompt_files_exist(self, prompts_dir: Path) -> None:
        """Verify all 13 POS prompt JSON files exist."""
        expected_files = [
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

        for filename in expected_files:
            filepath = prompts_dir / filename
            assert filepath.exists(), f"Prompt file {filename} does not exist"
            assert filepath.is_file(), f"Prompt file {filename} is not a regular file"

    def test_prompt_files_are_valid_json(self, prompts_dir: Path) -> None:
        """Verify all prompt files contain valid JSON."""
        prompt_files = [
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

        for filename in prompt_files:
            filepath = prompts_dir / filename
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    json.load(f)
                except json.JSONDecodeError as e:
                    pytest.fail(f"File {filename} contains invalid JSON: {e}")

    @pytest.mark.parametrize(
        "pos_file",
        [
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
        ],
    )
    def test_prompt_loads_as_chat_prompt_template(self, prompts_dir: Path, pos_file: str) -> None:
        """Test that each prompt JSON loads correctly as ChatPromptTemplate."""
        filepath = prompts_dir / pos_file

        # Load the prompt using core.prompts.load_prompt function
        loaded = load_prompt(str(filepath))

        # Verify it's a ChatPromptTemplate
        assert isinstance(loaded, ChatPromptTemplate), f"Prompt {pos_file} did not load as ChatPromptTemplate"
