"""Dutch to Russian conjunction details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuConjunctionDetails(BaseModel):
    """Detailed information for Dutch conjunctions with Russian explanations."""

    conjunction_type: str  # coordinating/subordinating in Russian
    word_order_effect: str  # Russian explanation
    shared: SharedLearningFields
