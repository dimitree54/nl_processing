# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused
from nl_processing.database.service import save_translation

# Benchmark utilities used by integration tests at runtime (not detected by static analysis)
from nl_processing.extract_text_from_image.benchmark import run_benchmark
from nl_processing.extract_words_from_text.service import WordExtractor
from nl_processing.translate_text.service import TextTranslator
from nl_processing.translate_word.service import WordTranslator

__all__ = [
    "save_translation",
    "run_benchmark",
    "WordExtractor",
    "TextTranslator",
    "WordTranslator",
]
