"""Progress-related shared models."""

from datetime import datetime

from pydantic import BaseModel

from nl_processing.core.models import WordPair, WordPairSnapshot


class PersonalWord(BaseModel):
    """Full personal-vocabulary entry with stable IDs, added_at, and scores."""

    pair: WordPair
    source_word_id: int
    target_word_id: int
    added_at: datetime
    scores: dict[str, int]


class ExerciseProgressSummary(BaseModel):
    """Per-exercise-type progress report."""

    total_words: int
    negative_words: int
    negative_ratio: float
    negative_percentage: float


class EnrichedWordPairSnapshot(WordPairSnapshot):
    """Snapshot with added_at for cache-side personal-vocabulary reads."""

    added_at: datetime
