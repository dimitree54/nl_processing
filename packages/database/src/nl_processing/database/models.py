from datetime import datetime

from nl_processing.core.models import Word, WordPairSnapshot
from pydantic import BaseModel


class AddWordsResult(BaseModel):
    new_words: list[Word]
    existing_words: list[Word]


class EnrichedWordPairSnapshot(WordPairSnapshot):
    """Snapshot with added_at for cache-side personal-vocabulary reads (FR-10, CR-3)."""

    added_at: datetime
