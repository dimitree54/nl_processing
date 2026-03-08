from nl_processing.core.models import Word
from pydantic import BaseModel


class AddWordsResult(BaseModel):
    new_words: list[Word]
    existing_words: list[Word]
