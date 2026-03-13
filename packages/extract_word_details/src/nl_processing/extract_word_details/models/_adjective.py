"""Dutch to Russian adjective details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuAdjectiveDetails(BaseModel):
    """Detailed information for Dutch adjectives with Russian explanations."""

    comparative: str | None = None
    superlative: str | None = None
    inflected_form: str | None = None  # with -e
    usage_explanation: str  # Russian explanation
    shared: SharedLearningFields
