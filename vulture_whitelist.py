# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused after T1 legacy cleanup
from nl_processing.database.service import save_translation

# Benchmark utilities used by integration tests at runtime (not detected by static analysis)
from nl_processing.extract_text_from_image.benchmark import run_benchmark

__all__ = ["save_translation", "run_benchmark"]
