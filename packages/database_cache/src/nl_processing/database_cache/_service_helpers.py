"""Helper functions extracted from service.py for code organization."""

from datetime import datetime

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair


def _parse_dt(meta: dict[str, str | int], key: str) -> datetime | None:
    val = meta[key] if key in meta else None
    if val is None:
        return None
    return datetime.fromisoformat(str(val))


def row_to_word_pair(
    row: dict[str, str | int],
    source_language: Language,
    target_language: Language,
) -> WordPair:
    """Convert database row to WordPair object with explicit language parameters."""
    return WordPair(
        source=Word(
            normalized_form=str(row["source_normalized_form"]),
            word_type=PartOfSpeech(row["source_word_type"]),
            language=source_language,
        ),
        target=Word(
            normalized_form=str(row["target_normalized_form"]),
            word_type=PartOfSpeech(row["target_word_type"]),
            language=target_language,
        ),
    )
