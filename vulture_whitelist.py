# Vulture whitelist — list false-positive "unused" symbols here.

# Functions that are owned by future sprints but flagged as unused after T1 legacy cleanup
from nl_processing.database.service import save_translation

__all__ = ["save_translation"]
