from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend

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

check_event_applied  # noqa: F821
mark_event_applied  # noqa: F821
integration_schema_ready  # noqa: F821
some_other_method  # noqa: F821
args  # noqa: F821
kwargs  # noqa: F821
cls  # noqa: F821

__all__ = ["AbstractBackend", "NeonBackend"]
