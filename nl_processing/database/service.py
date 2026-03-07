"""DatabaseService — primary public class of the database module.

Provides add_words(), get_words(), and create_tables() for persisting
and retrieving Word objects backed by Neon PostgreSQL.
"""

import asyncio
import os

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import ConfigurationError
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.translate_word.service import WordTranslator

_logger = get_logger("service")

_DATABASE_URL_MISSING = (
    "DATABASE_URL environment variable is required. "
    "Set it to your Neon PostgreSQL connection string. "
    "See: https://neon.tech/docs/connect/connect-from-any-app"
)


def _read_database_url() -> str:
    """Read DATABASE_URL from environment, raising ConfigurationError if absent."""
    try:
        return os.environ["DATABASE_URL"]
    except KeyError as exc:
        raise ConfigurationError(_DATABASE_URL_MISSING) from exc


class DatabaseService:
    """Async service for persisting and retrieving words with translations."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
    ) -> None:
        database_url = _read_database_url()
        self._backend = NeonBackend(database_url)
        self._translator = WordTranslator(
            source_language=source_language,
            target_language=target_language,
        )
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        src = source_language.value
        tgt = target_language.value
        self._source_table = src
        self._target_table = tgt
        self._translations_table = f"{src}_{tgt}"

    async def add_words(self, words: list[Word]) -> AddWordsResult:
        """Add words to the corpus and associate them with the current user.

        New words trigger fire-and-forget async translation.
        Returns feedback on which words were new vs already existing.
        """
        if not words:
            return AddWordsResult(new_words=[], existing_words=[])

        new_words: list[Word] = []
        existing_words: list[Word] = []

        for word in words:
            table = word.language.value
            word_id = await self._backend.add_word(table, word.normalized_form, word.word_type.value)
            if word_id is None:
                existing_words.append(word)
                row = await self._backend.get_word(table, word.normalized_form)
                word_id = int(row["id"])  # type: ignore[index]
            else:
                new_words.append(word)
            await self._backend.add_user_word(self._user_id, word_id, word.language.value)

        if new_words:
            asyncio.create_task(self._translate_and_store(new_words))

        return AddWordsResult(new_words=new_words, existing_words=existing_words)

    async def _translate_and_store(self, new_words: list[Word]) -> None:
        """Translate new words and store translations (fire-and-forget)."""
        try:
            translated = await self._translator.translate(new_words)
            for source_word, target_word in zip(new_words, translated):
                target_id = await self._backend.add_word(
                    self._target_table,
                    target_word.normalized_form,
                    target_word.word_type.value,
                )
                if target_id is None:
                    row = await self._backend.get_word(self._target_table, target_word.normalized_form)
                    target_id = int(row["id"])  # type: ignore[index]
                source_row = await self._backend.get_word(self._source_table, source_word.normalized_form)
                source_id = int(source_row["id"])  # type: ignore[index]
                await self._backend.add_translation_link(self._translations_table, source_id, target_id)
            _logger.info("Translated and stored %d words", len(new_words))
        except Exception:
            _logger.warning(
                "Background translation failed for %d words",
                len(new_words),
                exc_info=True,
            )

    async def get_words(
        self,
        *,
        word_type: PartOfSpeech | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Return translated word pairs for the current user.

        Only words with completed translations are included
        (backend uses INNER JOIN).
        """
        rows = await self._backend.get_user_words(
            self._user_id,
            self._source_language.value,
            word_type=word_type.value if word_type else None,
            limit=limit,
            random=random,
        )
        pairs: list[WordPair] = []
        for row in rows:
            source = Word(
                normalized_form=str(row["source_normalized_form"]),
                word_type=PartOfSpeech(row["source_word_type"]),
                language=self._source_language,
            )
            target = Word(
                normalized_form=str(row["target_normalized_form"]),
                word_type=PartOfSpeech(row["target_word_type"]),
                language=self._target_language,
            )
            pairs.append(WordPair(source=source, target=target))
        return pairs

    @classmethod
    async def create_tables(cls) -> None:
        """Create all required database tables (idempotent)."""
        database_url = _read_database_url()
        backend = NeonBackend(database_url)
        await backend.create_tables(languages=["nl", "ru"], pairs=[("nl", "ru")])
