"""DatabaseService — primary public class of the database module.

Provides add_words(), get_words(), and create_tables() for persisting
and retrieving Word objects backed by Neon PostgreSQL.
"""

import asyncio
from datetime import datetime
import os
from typing import Protocol

from nl_processing.core.models import Language, PartOfSpeech, Word, WordPair

from nl_processing.database import _translation
from nl_processing.database._row_helpers import row_to_word_pair
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.backend.neon import NeonBackend
from nl_processing.database.exceptions import ConfigurationError
from nl_processing.database.logging import get_logger
from nl_processing.database.models import AddWordsResult, PersonalWord

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
            database_url = _read_database_url()
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

        new_source_words = [word for word in new_words if word.language == self._source_language]
        if new_source_words and self._translator is not None:
            asyncio.create_task(
                _translation.translate_and_store(
                    self._backend,
                    self._translator,
                    self._source_table,
                    self._target_table,
                    self._translations_table,
                    new_source_words,
                    _logger,
                )
            )

        return AddWordsResult(new_words=new_words, existing_words=existing_words)

    async def list_personal_words(self, exercise_types: list[str] | None = None) -> list[PersonalWord]:
        """Return personal word entries with scores for the given exercise types."""
        rows = await self._backend.get_user_words(self._user_id, self._source_language.value)
        if not rows:
            return []

        scores_by_word: dict[int, dict[str, int]] = {}
        if exercise_types:
            source_word_ids = [int(row["source_id"]) for row in rows]  # type: ignore[arg-type]
            for exercise_type in exercise_types:
                table = f"{self._source_language.value}_{self._target_language.value}_{exercise_type}"
                score_rows = await self._backend.get_user_exercise_scores(table, self._user_id, source_word_ids)
                for score_row in score_rows:
                    wid = int(score_row["source_word_id"])
                    scores_by_word.setdefault(wid, {})[exercise_type] = int(score_row["score"])
        result = []
        for row in rows:
            pair = row_to_word_pair(row, self._source_language, self._target_language)
            source_word_id = int(row["source_id"])  # type: ignore[arg-type]
            target_word_id = int(row["target_id"])  # type: ignore[arg-type]
            added_at_raw = row["added_at"]
            added_at = added_at_raw if isinstance(added_at_raw, datetime) else datetime.now()

            scores = {}
            if exercise_types:
                word_scores = scores_by_word.get(source_word_id, {})
                scores = {et: word_scores.get(et, 0) for et in exercise_types}

            result.append(
                PersonalWord(
                    pair=pair,
                    source_word_id=source_word_id,
                    target_word_id=target_word_id,
                    added_at=added_at,
                    scores=scores,
                )
            )
        return result

    async def get_words(
        self,
        *,
        word_type: PartOfSpeech | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Return translated word pairs for the current user."""
        rows = await self._backend.get_user_words(
            self._user_id,
            self._source_language.value,
            word_type=word_type.value if word_type else None,
            limit=limit,
            random=random,
        )
        pairs = []
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
        if limit is None and not random:
            total_count = await self._backend.count_user_words(
                self._user_id,
                self._source_language.value,
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

    @classmethod
    async def create_tables(cls, exercise_slugs: list[str] | None = None) -> None:
        """Create all required database tables (idempotent)."""
        database_url = _read_database_url()
        backend = NeonBackend(database_url)
        await backend.create_tables(
            languages=["nl", "ru"],
            pairs=[("nl", "ru")],
            exercise_slugs=exercise_slugs or [],
        )
