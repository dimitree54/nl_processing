"""Dutch to Russian verb details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuVerbDetails(BaseModel):
    """Detailed information for Dutch verbs with Russian explanations."""

    present_tense: dict[str, str]  # ik/jij/hij/wij/zij forms
    past_simple: str
    past_participle: str
    auxiliary: str  # hebben/zijn
    separable_prefix: str | None = None
    conjugation_explanation: str  # Russian explanation
    shared: SharedLearningFields
