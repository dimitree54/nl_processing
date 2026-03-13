"""Dutch to Russian proper noun details models."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuProperNounPersonDetails(BaseModel):
    """Detailed information for Dutch proper nouns (person) with Russian explanations."""

    origin_explanation: str  # Russian explanation
    cultural_context: str  # Russian explanation
    shared: SharedLearningFields


class NlRuProperNounCountryDetails(BaseModel):
    """Detailed information for Dutch proper nouns (country) with Russian explanations."""

    dutch_name: str
    russian_name: str
    nationality_adjective: str  # Dutch
    nationality_noun: str  # Dutch
    cultural_context: str  # Russian explanation
    shared: SharedLearningFields
