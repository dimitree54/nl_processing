"""Base models for detailed word extraction.

Contains shared learning fields used by all POS-specific models.
All explanatory text is in Russian per FR-6 and DEC-4.
"""

from pydantic import BaseModel


class CommonPhrase(BaseModel):
    """A phrase or expression that commonly includes this word."""

    phrase: str
    translation: str


class ExampleSentence(BaseModel):
    """Example sentence demonstrating word usage."""

    dutch_sentence: str
    russian_explanation: str


class WordPartExplanation(BaseModel):
    """Explanation of word components like roots, prefixes, suffixes."""

    part: str
    explanation_russian: str


class InterestingFact(BaseModel):
    """Cultural or linguistic fact about the word."""

    fact_russian: str
    dutch_parallel: str | None = None


class SharedLearningFields(BaseModel):
    """Common learning-oriented fields shared across all POS models."""

    common_phrases: list[CommonPhrase]
    example_sentences: list[ExampleSentence]
    word_parts: list[WordPartExplanation]
    interesting_facts: list[InterestingFact]
