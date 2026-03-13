from pydantic import BaseModel

from nl_processing.core.models import WordPair


class TieredCandidate(BaseModel):
    """Tiered exercise candidate with scores and repeat mode state."""

    pair: WordPair
    source_word_id: int
    scores: dict[str, int]
    in_repeat_mode: bool


class TieredExerciseSelection(BaseModel):
    """Selected exercise with context for tiered practice flows."""

    pair: WordPair
    source_word_id: int
    exercise_type: str
    in_repeat_mode: bool


class TieredProgressSummary(BaseModel):
    """Progress summary for tiered exercise system."""

    total_words: int
    fully_completed_words: int
    completion_ratio: float


class TieredSnapshotEntry(BaseModel):
    """Remote snapshot entry for cache rebuilds with tiered scores."""

    source_word_id: int
    target_word_id: int
    pair: WordPair
    scores: dict[str, int]
    in_repeat_mode: bool
