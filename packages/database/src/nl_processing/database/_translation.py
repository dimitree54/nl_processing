"""Background translation and storage for DatabaseService."""

from typing import Protocol

from nl_processing.core.models import Word


class WordTranslatorProtocol(Protocol):
    async def translate(self, words: list[Word]) -> list[Word]: ...


class LoggerProtocol(Protocol):
    def info(self, msg: object, *args: object, **kwargs: object) -> None: ...
    def warning(self, msg: object, *args: object, **kwargs: object) -> None: ...


class BackendProtocol(Protocol):
    async def add_word(self, table: str, normalized_form: str, word_type: str) -> int | None: ...
    async def get_word(self, table: str, normalized_form: str) -> dict[str, str | int] | None: ...
    async def add_translation_link(self, table: str, source_id: int, target_id: int) -> None: ...


async def translate_and_store(
    backend: BackendProtocol,
    translator: WordTranslatorProtocol,
    target_table: str,
    translations_table: str,
    word_id_pairs: list[tuple[Word, int]],
    logger: LoggerProtocol,
) -> None:
    """Translate new words and store translations (fire-and-forget)."""
    try:
        source_words = [word for word, _ in word_id_pairs]
        translated = await translator.translate(source_words)
        for (source_word, source_id), target_word in zip(word_id_pairs, translated):
            target_id = await backend.add_word(
                target_table,
                target_word.normalized_form,
                target_word.word_type.value,
            )
            if target_id is None:
                row = await backend.get_word(target_table, target_word.normalized_form)
                target_id = int(row["id"])  # type: ignore[index]
            await backend.add_translation_link(translations_table, source_id, target_id)
        logger.info("Translated and stored %d words", len(source_words))
    except Exception:
        logger.warning(
            "Background translation failed for %d words",
            len(source_words),
            exc_info=True,
        )
