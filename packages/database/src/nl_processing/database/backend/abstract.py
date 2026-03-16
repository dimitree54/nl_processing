"""Re-export AbstractBackend from database_core for legacy compatibility."""

from nl_processing.database_core.backend.abstract import AbstractBackend

__all__ = ["AbstractBackend"]
