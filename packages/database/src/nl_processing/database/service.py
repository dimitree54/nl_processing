"""DatabaseService — primary public class of the database module.

Provides add_words(), get_words(), and create_tables() for persisting
and retrieving Word objects backed by Neon PostgreSQL.
"""

from typing import Protocol

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair
from nl_processing.database_core._database_config import read_database_url
from nl_processing.database_core.backend.abstract import AbstractBackend
from nl_processing.database_core.backend.neon import NeonBackend

from nl_processing.database import _translation
from nl_processing.database._background_tasks import BackgroundTaskManager
from nl_processing.database._service_helpers import get_words_impl
from nl_processing.database._user_operations import delete_word_impl
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult

_logger = get_logger("service")


class WordTranslatorProtocol(Protocol):
    async def translate(self, words: list[Word]) -> list[Word]: ...


class DatabaseService:
    """Async service for persisting and retrieving words with translations."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
        backend: AbstractBackend | None = None,
        translator: WordTranslatorProtocol | None = None,
    ) -> None:
        if backend is None:
            database_url = read_database_url()
            self._backend: AbstractBackend = NeonBackend(database_url)
        else:
            self._backend = backend
        self._translator = translator
        self._user_id = user_id
        self._source_language = source_language
        self._target_language = target_language
        src = source_language.value
        tgt = target_language.value
        self._source_table = src
        self._target_table = tgt
        self._translations_table = f"{src}_{tgt}"
        # Track background translation tasks owned by this service instance
        self._task_manager = BackgroundTaskManager()

    async def add_words(self, words: list[Word]) -> AddWordsResult:
        """Add words to the corpus and associate them with the current user.

        New words trigger fire-and-forget async translation.
        Returns feedback on which words were new vs already existing.
        """
        if not words:
            return AddWordsResult(new_words=[], existing_words=[])

        new_words: list[Word] = []
        existing_words: list[Word] = []
        new_source_word_pairs: list[tuple[Word, int]] = []

        for word in words:
            table = word.language.value
            word_id = await self._backend.add_word(table, word.normalized_form, word.word_type.value)
            if word_id is None:
                existing_words.append(word)
                row = await self._backend.get_word(table, word.normalized_form)
                word_id = int(row["id"])  # type: ignore[index]
            else:
                new_words.append(word)
                if word.language == self._source_language:
                    new_source_word_pairs.append((word, word_id))
            await self._backend.add_user_word(self._user_id, word_id, word.language.value)

        if new_source_word_pairs and self._translator is not None:
            self._task_manager.create_translation_task(self._delayed_translation, new_source_word_pairs)

        return AddWordsResult(new_words=new_words, existing_words=existing_words)

    async def get_words(
        self,
        *,
        word_type: PartOfSpeech | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Return translated word pairs for the current user."""
        return await get_words_impl(
            self._backend,
            self._user_id,
            self._source_language,
            self._target_language,
            word_type=word_type,
            limit=limit,
            random=random,
        )

    async def delete_word(self, source_word_id: int, exercise_types: list[str] | None = None) -> None:
        """Delete one personal-vocabulary entry (FR-9, BR-7, FM-5)."""
        await delete_word_impl(
            self._backend,
            self._user_id,
            source_word_id,
            self._source_language,
            self._target_language,
            exercise_types,
        )

    async def delete_words(self, source_word_ids: list[int], exercise_types: list[str] | None = None) -> None:
        """Delete many personal-vocabulary entries (FR-9)."""
        for source_word_id in source_word_ids:
            await self.delete_word(source_word_id, exercise_types=exercise_types)

    async def _delayed_translation(self, word_id_pairs: list[tuple[Word, int]]) -> None:
        """Run translation using a fresh backend instance to avoid connection conflicts."""
        # For unit tests with MockBackend, reuse the same instance
        # For real backends, create a fresh instance to avoid connection conflicts
        if self._backend.__class__.__name__ == "MockBackend":
            fresh_backend = self._backend
        else:
            fresh_backend = NeonBackend(read_database_url())

        await _translation.translate_and_store(
            fresh_backend,
            self._translator,
            self._target_table,
            self._translations_table,
            word_id_pairs,
            _logger,
            fail_fast=True,
        )

    async def wait_for_background_translations(self) -> None:
        """Wait for all background translation tasks owned by this service instance to complete.

        This method must be called before service teardown to ensure
        background translation tasks don't outlive schema teardown.
        Surfaces real task errors to the caller instead of silently swallowing them.
        """
        await self._task_manager.wait_for_background_translations()

    @classmethod
    async def create_tables(cls, exercise_slugs: list[str] | None = None) -> None:
        """Create all required database tables (idempotent)."""
        database_url = read_database_url()
        backend = NeonBackend(database_url)
        await backend.create_tables(
            languages=["nl", "ru"],
            pairs=[("nl", "ru")],
            exercise_slugs=exercise_slugs or [],
        )
