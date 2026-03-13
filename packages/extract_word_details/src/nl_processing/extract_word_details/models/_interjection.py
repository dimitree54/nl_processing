"""Dutch to Russian interjection details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuInterjectionDetails(BaseModel):
    """Detailed information for Dutch interjections with Russian explanations."""

    emotion_or_context: str  # Russian explanation
    formality_level: str  # Russian explanation
    shared: SharedLearningFields
