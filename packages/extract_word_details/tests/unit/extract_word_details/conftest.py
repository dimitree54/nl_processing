"""Shared test fixtures for POS model tests."""

import json
from pathlib import Path

from langchain_core.load import load
from langchain_core.prompts import ChatPromptTemplate
import pytest

from nl_processing.extract_word_details._base_models import (
    CommonPhrase,
    ExampleSentence,
    InterestingFact,
    SharedLearningFields,
    WordPartExplanation,
)


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


@pytest.fixture
def prompts_dir() -> Path:
    """Path to the prompts directory."""
    return Path(__file__).parents[3] / "src" / "nl_processing" / "extract_word_details" / "prompts"


@pytest.fixture
def shared_fields() -> SharedLearningFields:
    """Sample shared learning fields for testing."""
    return SharedLearningFields(
        common_phrases=[CommonPhrase(phrase="test phrase", translation="тестовая фраза")],
        example_sentences=[ExampleSentence(dutch_sentence="Test.", russian_explanation="Тест.")],
        word_parts=[WordPartExplanation(part="test", explanation_russian="тестовый корень")],
        interesting_facts=[InterestingFact(fact_russian="интересный факт")],
    )
