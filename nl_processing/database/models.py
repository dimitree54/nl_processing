from pydantic import BaseModel

from nl_processing.core.models import Word


class AddWordsResult(BaseModel):
    new_words: list[Word]
    existing_words: list[Word]


class WordPair(BaseModel):
    source: Word
    target: Word


class ScoredWordPair(BaseModel):
    pair: WordPair
    scores: dict[str, int]
