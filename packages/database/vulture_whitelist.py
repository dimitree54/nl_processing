from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend

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

integration_schema_ready  # noqa: F821
some_other_method  # noqa: F821
args  # noqa: F821
kwargs  # noqa: F821
cls  # noqa: F821

__all__ = ["AbstractBackend", "NeonBackend"]
