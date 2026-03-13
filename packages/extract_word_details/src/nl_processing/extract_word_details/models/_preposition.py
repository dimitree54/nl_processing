"""Dutch to Russian preposition details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuPrepositionDetails(BaseModel):
    """Detailed information for Dutch prepositions with Russian explanations."""

    case_governance: str  # Russian explanation of what follows this prep
    spatial_or_temporal: str  # Russian explanation
    shared: SharedLearningFields
