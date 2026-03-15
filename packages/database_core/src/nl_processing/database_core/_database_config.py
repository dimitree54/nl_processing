"""Shared database configuration helpers."""

import os

from nl_processing.core.models import Language

from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend
from nl_processing.database_core.exceptions import ConfigurationError

_DATABASE_URL_MISSING = (
    "DATABASE_URL environment variable is required. "
    "Set it to your Neon PostgreSQL connection string. "
    "See: https://neon.tech/docs/connect/connect-from-any-app"
)


def read_database_url() -> str:
    """Read DATABASE_URL from environment, raising ConfigurationError if absent."""
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise ConfigurationError(_DATABASE_URL_MISSING) from exc


def _init_backend_and_tables(
    exercise_types: list[str],
    source_language: Language,
    target_language: Language,
    backend: AbstractBackend | None = None,
) -> tuple[AbstractBackend, dict[str, str], str]:
    """Shared backend initialization and table name setup."""
    if not exercise_types:
        msg = "exercise_types must be a non-empty list"
        raise ValueError(msg)

    if backend is None:
        database_url = read_database_url()
        backend = NeonBackend(database_url)

    src = source_language.value
    tgt = target_language.value
    score_tables = {et: f"{src}_{tgt}_{et}" for et in exercise_types}
    applied_events_table = f"applied_events_{src}_{tgt}"
    return backend, score_tables, applied_events_table
