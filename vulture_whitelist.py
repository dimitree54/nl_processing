# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import ConfigurationError, DatabaseError
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult, ScoredWordPair
from nl_processing.database.service import DatabaseService
from nl_processing.database.testing import (
    count_translation_links,
    count_user_words,
    count_words,
    reset_database,
)

# Benchmark utilities used by integration tests at runtime (not detected by static analysis)
from nl_processing.extract_text_from_image.benchmark import run_benchmark
from nl_processing.extract_words_from_text.service import WordExtractor
from nl_processing.sampling.service import WordSampler
from nl_processing.translate_text.service import TextTranslator
from nl_processing.translate_word.service import WordTranslator
from tests.e2e.database.conftest import db_ready, wait_for_translations

# AbstractBackend ABC — methods are abstract, implemented by concrete backends (T4+)
AbstractBackend.add_word  # type: ignore[misc]
AbstractBackend.get_word  # type: ignore[misc]
AbstractBackend.add_translation_link  # type: ignore[misc]
AbstractBackend.get_user_words  # type: ignore[misc]
AbstractBackend.add_user_word  # type: ignore[misc]
AbstractBackend.increment_user_exercise_score  # type: ignore[misc]
AbstractBackend.get_user_exercise_scores  # type: ignore[misc]
AbstractBackend.check_event_applied  # type: ignore[misc]
AbstractBackend.mark_event_applied  # type: ignore[misc]
AbstractBackend.apply_score_delta_atomic  # type: ignore[misc]
AbstractBackend.create_tables  # type: ignore[misc]

# Abstract method parameters — unused in ABC bodies, used by concrete implementations
table  # noqa: F821
normalized_form  # noqa: F821
word_type  # noqa: F821
source_id  # noqa: F821
target_id  # noqa: F821
user_id  # noqa: F821
word_id  # noqa: F821
language  # noqa: F821
limit  # noqa: F821
random  # noqa: F821, A001
source_word_id  # noqa: F821
exercise_type  # noqa: F821
delta  # noqa: F821
source_word_ids  # noqa: F821
exercise_types  # noqa: F821
languages  # noqa: F821
pairs  # noqa: F821
exercise_slugs  # noqa: F821
event_id  # noqa: F821
score_table  # noqa: F821
events_table  # noqa: F821

# Database model fields — used by subsequent tasks (T3-T14)
AddWordsResult.new_words  # type: ignore[misc]
AddWordsResult.existing_words  # type: ignore[misc]
ScoredWordPair.scores  # type: ignore[misc]
ScoredWordPair.source_word_id  # type: ignore[misc]
ScoredWordPair.pair.source  # type: ignore[union-attr]
ScoredWordPair.pair.target  # type: ignore[union-attr]

# DatabaseService — public API, used by consuming code / future tasks (T6+)
DatabaseService.add_words  # type: ignore[misc]
DatabaseService.get_words  # type: ignore[misc]
DatabaseService.create_tables  # type: ignore[misc]

# ExerciseProgressStore — internal API, used by sampling module (T12+)
ExerciseProgressStore.increment  # type: ignore[misc]
ExerciseProgressStore.get_word_pairs_with_scores  # type: ignore[misc]
ExerciseProgressStore.export_remote_snapshot  # type: ignore[misc]
ExerciseProgressStore.apply_score_delta  # type: ignore[misc]

# WordSampler — public API of sampling module, consumed by exercise runner (T13+)
WordSampler.sample  # type: ignore[misc]
WordSampler.sample_adversarial  # type: ignore[misc]

# classmethod first parameter — required by Python, flagged by vulture
cls  # noqa: F821

# NeonBackend — concrete implementation, used by T5+ (DatabaseService)
NeonBackend.create_tables  # type: ignore[misc]
NeonBackend.add_word  # type: ignore[misc]
NeonBackend.get_word  # type: ignore[misc]
NeonBackend.add_translation_link  # type: ignore[misc]
NeonBackend.get_user_words  # type: ignore[misc]
NeonBackend.add_user_word  # type: ignore[misc]
NeonBackend.increment_user_exercise_score  # type: ignore[misc]
NeonBackend.get_user_exercise_scores  # type: ignore[misc]
NeonBackend.check_event_applied  # type: ignore[misc]
NeonBackend.mark_event_applied  # type: ignore[misc]
NeonBackend.apply_score_delta_atomic  # type: ignore[misc]

__all__ = [
    "DatabaseService",
    "ConfigurationError",
    "DatabaseError",
    "ExerciseProgressStore",
    "get_logger",
    "AddWordsResult",
    "ScoredWordPair",
    "AbstractBackend",
    "NeonBackend",
    "run_benchmark",
    "WordExtractor",
    "TextTranslator",
    "WordTranslator",
    "count_translation_links",
    "count_user_words",
    "count_words",
    "reset_database",
    "WordSampler",
    "db_ready",
    "wait_for_translations",
]
