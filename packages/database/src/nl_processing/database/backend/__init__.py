"""Backend compatibility exports for database package.

This module provides compatibility shims for legacy imports from the database package's backend module.
The actual implementations are in database_core.
"""

from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend

__all__ = ["AbstractBackend", "NeonBackend"]
