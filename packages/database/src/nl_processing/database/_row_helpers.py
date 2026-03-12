"""Helper functions for converting backend row data to core models."""

from datetime import datetime

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair


def word_from_row(
    row: dict[str, str | int | datetime],
    prefix: str,
    lang: Language,
) -> Word:
    """Reconstruct a Word from a backend row using column prefix."""
    return Word(
        normalized_form=str(row[f"{prefix}_normalized_form"]),
        word_type=PartOfSpeech(row[f"{prefix}_word_type"]),
        language=lang,
    )


def row_to_word_pair(
    row: dict[str, str | int | datetime],
    source_language: Language,
    target_language: Language,
) -> WordPair:
    """Reconstruct a WordPair from a backend row dict."""
    return WordPair(
        source=word_from_row(row, "source", source_language),
        target=word_from_row(row, "target", target_language),
    )
