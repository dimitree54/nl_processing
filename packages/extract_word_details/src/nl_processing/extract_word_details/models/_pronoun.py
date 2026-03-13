"""Dutch to Russian pronoun details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuPronounDetails(BaseModel):
    """Detailed information for Dutch pronouns with Russian explanations."""

    pronoun_type: str  # personal/possessive/demonstrative etc. in Russian
    declension_forms: list[str]  # list of forms
    shared: SharedLearningFields
