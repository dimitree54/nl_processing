"""Dutch to Russian verb details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class PresentTenseConjugation(BaseModel):
    """Present tense conjugation forms for a Dutch verb."""

    ik: str
    jij: str
    hij: str
    wij: str
    zij: str


class PastSimpleConjugation(BaseModel):
    """Past simple (imperfectum) forms for a Dutch verb."""

    singular: str
    plural: str


class NlRuVerbDetails(BaseModel):
    """Detailed information for Dutch verbs with Russian explanations."""

    present_tense: PresentTenseConjugation
    past_simple: PastSimpleConjugation
    past_participle: str
    auxiliary: str  # hebben/zijn
    separable_prefix: str | None = None
    conjugation_explanation: str  # Russian explanation
    shared: SharedLearningFields
