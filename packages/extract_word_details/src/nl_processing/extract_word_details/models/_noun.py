"""Dutch to Russian noun details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuNounDetails(BaseModel):
    """Detailed information for Dutch nouns with Russian explanations."""

    article: str  # de/het
    plural: str | None = None
    diminutive: str | None = None
    gender_explanation: str  # Russian explanation
    shared: SharedLearningFields
