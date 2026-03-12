"""Service helper functions extracted to keep service.py under 200 lines."""

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair

from nl_processing.database.backend.abstract import AbstractBackend  # type: ignore[attr-defined]
from nl_processing.database.logging import get_logger

_logger = get_logger("service")


async def get_words_impl(
    backend: AbstractBackend,
    user_id: str,
    source_language: Language,
    target_language: Language,
    *,
    word_type: PartOfSpeech | None = None,
    limit: int | None = None,
    random: bool = False,
) -> list[WordPair]:
    """Return translated word pairs for the current user."""
    rows = await backend.get_user_words(
        user_id,
        source_language.value,
        word_type=word_type.value if word_type else None,
        limit=limit,
        random=random,
    )
    pairs = []
    for row in rows:
        source = Word(
            normalized_form=str(row["source_normalized_form"]),
            word_type=PartOfSpeech(row["source_word_type"]),
            language=source_language,
        )
        target = Word(
            normalized_form=str(row["target_normalized_form"]),
            word_type=PartOfSpeech(row["target_word_type"]),
            language=target_language,
        )
        pairs.append(WordPair(source=source, target=target))
    if limit is None and not random:
        total_count = await backend.count_user_words(
            user_id,
            source_language.value,
            word_type=word_type.value if word_type else None,
        )
        if total_count > len(pairs):
            excluded_count = total_count - len(pairs)
            _logger.warning(
                "%d of %d words excluded from get_words() due to missing translations",
                excluded_count,
                total_count,
            )
    return pairs
