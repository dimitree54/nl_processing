from nl_processing.core.models import WordPair
from pydantic import BaseModel


class TieredCandidate(BaseModel):
    pair: WordPair
    source_word_id: int
    scores: dict[str, int]
    in_repeat_mode: bool


class TieredProgressSummary(BaseModel):
    total_words: int
    fully_completed_words: int
    completion_ratio: float


class TieredSnapshotEntry(BaseModel):
    source_word_id: int
    target_word_id: int
    pair: WordPair
    scores: dict[str, int]
    in_repeat_mode: bool
