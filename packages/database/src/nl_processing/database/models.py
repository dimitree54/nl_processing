from datetime import datetime

from nl_processing.core.models import Word, WordPair, WordPairSnapshot
from pydantic import BaseModel


class AddWordsResult(BaseModel):
    new_words: list[Word]
    existing_words: list[Word]


class PersonalWord(BaseModel):
    """Full personal-vocabulary entry with stable IDs, added_at, and scores (FR-7)."""

    pair: WordPair
    source_word_id: int
    target_word_id: int
    added_at: datetime
    scores: dict[str, int]


class EnrichedWordPairSnapshot(WordPairSnapshot):
    """Snapshot with added_at for cache-side personal-vocabulary reads (FR-10, CR-3)."""

    added_at: datetime
