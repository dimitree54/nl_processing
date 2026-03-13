"""Dutch to Russian numeral details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuNumeralDetails(BaseModel):
    """Detailed information for Dutch numerals with Russian explanations."""

    numeral_type: str  # cardinal/ordinal in Russian
    ordinal_form: str | None = None
    shared: SharedLearningFields
