"""Dutch to Russian adverb details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuAdverbDetails(BaseModel):
    """Detailed information for Dutch adverbs with Russian explanations."""

    usage_context: str  # Russian explanation
    position_in_sentence: str  # Russian explanation
    shared: SharedLearningFields
