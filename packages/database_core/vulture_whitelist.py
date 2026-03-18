from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.backend._neon_connection import ConnectionManager

AbstractBackend.create_background_backend  # type: ignore[misc]
AbstractBackend.apply_score_delta_atomic  # type: ignore[misc]
AbstractBackend.upsert_word_details  # type: ignore[misc]
AbstractBackend.get_word_details  # type: ignore[misc]
AbstractBackend.get_word_details_batch  # type: ignore[misc]
NeonBackend.create_background_backend  # type: ignore[misc]
NeonBackend.apply_score_delta_atomic  # type: ignore[misc]
NeonBackend.upsert_word_details  # type: ignore[misc]
NeonBackend.get_word_details  # type: ignore[misc]
NeonBackend.get_word_details_batch  # type: ignore[misc]
ConnectionManager.database_url  # type: ignore[misc]

kwargs  # noqa: F821
cls  # noqa: F821

integration_schema_ready  # noqa: F821
_integration_schema_ready  # noqa: F821

__all__ = ["AbstractBackend", "NeonBackend"]
