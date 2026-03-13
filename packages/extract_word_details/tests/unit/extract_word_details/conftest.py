"""Shared test fixtures for POS model tests."""

import pytest

from nl_processing.extract_word_details._base_models import (
    CommonPhrase,
    ExampleSentence,
    InterestingFact,
    SharedLearningFields,
    WordPartExplanation,
)


@pytest.fixture
def shared_fields() -> SharedLearningFields:
    """Sample shared learning fields for testing."""
    return SharedLearningFields(
        common_phrases=[CommonPhrase(phrase="test phrase", translation="тестовая фраза")],
        example_sentences=[ExampleSentence(dutch_sentence="Test.", russian_explanation="Тест.")],
        word_parts=[WordPartExplanation(part="test", explanation_russian="тестовый корень")],
        interesting_facts=[InterestingFact(fact_russian="интересный факт")],
    )
