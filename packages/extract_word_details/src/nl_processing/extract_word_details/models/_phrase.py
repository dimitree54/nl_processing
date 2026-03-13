"""Dutch to Russian phrase details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuPhraseDetails(BaseModel):
    """Detailed information for Dutch phrases with Russian explanations."""

    literal_translation: str  # Russian
    figurative_meaning: str  # Russian explanation
    usage_context: str  # Russian explanation
    shared: SharedLearningFields
