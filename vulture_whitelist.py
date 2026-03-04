# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult, ScoredWordPair
from nl_processing.database.service import save_translation

# Benchmark utilities used by integration tests at runtime (not detected by static analysis)
from nl_processing.extract_text_from_image.benchmark import run_benchmark
from nl_processing.extract_words_from_text.service import WordExtractor
from nl_processing.translate_text.service import TextTranslator
from nl_processing.translate_word.service import WordTranslator

# Database model fields — used by subsequent tasks (T3-T14)
AddWordsResult.new_words  # type: ignore[misc]
AddWordsResult.existing_words  # type: ignore[misc]
ScoredWordPair.scores  # type: ignore[misc]
ScoredWordPair.pair.source  # type: ignore[union-attr]
ScoredWordPair.pair.target  # type: ignore[union-attr]

__all__ = [
    "save_translation",
    "ConfigurationError",
    "DatabaseError",
    "get_logger",
    "AddWordsResult",
    "ScoredWordPair",
    "run_benchmark",
    "WordExtractor",
    "TextTranslator",
    "WordTranslator",
]
