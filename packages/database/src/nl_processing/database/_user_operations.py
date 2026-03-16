"""User-specific database operations for DatabaseService."""

from nl_processing.core.models import Language
from nl_processing.database_core.backend.abstract import AbstractBackend

from nl_processing.database.exceptions import WordNotFoundError


async def delete_word_impl(
    backend: AbstractBackend,
    user_id: str,
    source_word_id: int,
    source_language: Language,
    target_language: Language,
    exercise_types: list[str] | None = None,
) -> None:
    """Implementation of delete_word operation."""

    exists = await backend.check_user_word_exists(
        user_id,
        source_word_id,
        source_language.value,
    )
    if not exists:
        raise WordNotFoundError(f"Source word ID {source_word_id} not in user's vocabulary")

    # Delete exercise scores first
    if exercise_types:
        src = source_language.value
        tgt = target_language.value
        for et in exercise_types:
            table = f"{src}_{tgt}_{et}"
            await backend.delete_user_exercise_score(table, user_id, source_word_id)

    # Delete user_words membership
    await backend.delete_user_word(user_id, source_word_id, source_language.value)
