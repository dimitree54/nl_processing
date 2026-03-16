"""Re-export NeonBackend from database_core for compatibility."""

from nl_processing.database_core.backend.neon import NeonBackend

__all__ = ["NeonBackend"]
