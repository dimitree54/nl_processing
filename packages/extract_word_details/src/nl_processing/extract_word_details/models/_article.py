"""Dutch to Russian article details model."""

from pydantic import BaseModel

from nl_processing.extract_word_details._base_models import SharedLearningFields


class NlRuArticleDetails(BaseModel):
    """Detailed information for Dutch articles with Russian explanations."""

    article_type: str  # definite/indefinite in Russian
    gender_rules: str  # Russian explanation
    shared: SharedLearningFields
