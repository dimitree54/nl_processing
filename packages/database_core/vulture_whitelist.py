from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.backend._neon_connection import ConnectionManager
from nl_processing.database_core._database_config import _init_backend_and_tables

AbstractBackend.check_event_applied  # type: ignore[misc]
AbstractBackend.mark_event_applied  # type: ignore[misc]
AbstractBackend.apply_score_delta_atomic  # type: ignore[misc]
AbstractBackend.upsert_word_details  # type: ignore[misc]
AbstractBackend.get_word_details  # type: ignore[misc]
AbstractBackend.get_word_details_batch  # type: ignore[misc]
NeonBackend.check_event_applied  # type: ignore[misc]
NeonBackend.mark_event_applied  # type: ignore[misc]
NeonBackend.apply_score_delta_atomic  # type: ignore[misc]
NeonBackend.upsert_word_details  # type: ignore[misc]
NeonBackend.get_word_details  # type: ignore[misc]
NeonBackend.get_word_details_batch  # type: ignore[misc]
ConnectionManager.create_fresh_connection  # type: ignore[misc]
ConnectionManager.get_database_url  # type: ignore[misc]

check_event_applied  # noqa: F821
mark_event_applied  # noqa: F821
kwargs  # noqa: F821
cls  # noqa: F821

_init_backend_and_tables  # type: ignore[misc]
integration_schema_ready  # noqa: F821
_integration_schema_ready  # noqa: F821

__all__ = ["AbstractBackend", "NeonBackend"]
