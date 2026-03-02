# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused after T1 legacy cleanup
from nl_processing.database.service import save_translation

# Benchmark utilities used by integration tests at runtime (not detected by static analysis)
from nl_processing.extract_text_from_image.benchmark import run_benchmark
from nl_processing.extract_words_from_text.service import extract_words_from_text
from nl_processing.translate_text.service import translate_text
from nl_processing.translate_word.service import translate_word

# pytest hooks called by pytest internals
from tests.e2e.conftest import pytest_addoption

__all__ = [
    "save_translation",
    "run_benchmark",
    "extract_words_from_text",
    "translate_text",
    "translate_word",
    "pytest_addoption",
]
