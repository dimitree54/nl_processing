"""NeonBackend — asyncpg implementation of AbstractBackend for Neon PostgreSQL."""

import asyncpg

from nl_processing.database.backend._queries import (
    ADD_USER_WORD,
    CREATE_USER_WORDS,
    add_translation_link_query,
    add_word_query,
    create_exercise_scores_table,
    create_translations_table,
    create_words_table,
    get_scores_query,
    get_user_words_query,
    get_word_query,
    increment_score_query,
)
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.exceptions import DatabaseError
from nl_processing.database.logging import get_logger

_logger = get_logger("backend")


class NeonBackend(AbstractBackend):
    """Concrete asyncpg backend targeting Neon PostgreSQL."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._connection: asyncpg.Connection | None = None  # type: ignore[type-arg]

    async def _connect(self) -> asyncpg.Connection:  # type: ignore[type-arg]
        """Return cached connection, creating it lazily on first call."""
        if self._connection is None:
            try:
                self._connection = await asyncpg.connect(dsn=self._database_url)
                _logger.info("Connected to Neon PostgreSQL")
            except asyncpg.PostgresError as exc:
                raise DatabaseError(str(exc)) from exc
            except OSError as exc:
                raise DatabaseError(str(exc)) from exc
        return self._connection

    async def create_tables(
        self,
        languages: list[str],
        pairs: list[tuple[str, str]],
    ) -> None:
        conn = await self._connect()
        try:
            for lang in languages:
                await conn.execute(create_words_table(lang))
            for src, tgt in pairs:
                await conn.execute(create_translations_table(src, tgt))
            await conn.execute(CREATE_USER_WORDS)
            for src, tgt in pairs:
                await conn.execute(create_exercise_scores_table(src, tgt))
            _logger.info("Created tables for languages=%s pairs=%s", languages, pairs)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc

    async def add_word(
        self,
        table: str,
        normalized_form: str,
        word_type: str,
    ) -> int | None:
        conn = await self._connect()
        try:
            row = await conn.fetchrow(add_word_query(table), normalized_form, word_type)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        if row is None:
            return None
        return int(row["id"])

    async def get_word(
        self,
        table: str,
        normalized_form: str,
    ) -> dict[str, str | int] | None:
        conn = await self._connect()
        try:
            row = await conn.fetchrow(get_word_query(table), normalized_form)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        if row is None:
            return None
        return {"id": row["id"], "normalized_form": row["normalized_form"], "word_type": row["word_type"]}

    async def add_translation_link(
        self,
        table: str,
        source_id: int,
        target_id: int,
    ) -> None:
        conn = await self._connect()
        try:
            await conn.execute(add_translation_link_query(table), source_id, target_id)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc

    async def add_user_word(
        self,
        user_id: str,
        word_id: int,
        language: str,
    ) -> None:
        conn = await self._connect()
        try:
            await conn.execute(ADD_USER_WORD, user_id, word_id, language)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc

    # jscpd:ignore-start — method signature must match AbstractBackend ABC
    async def get_user_words(
        self,
        user_id: str,
        language: str,
        word_type: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[dict[str, str | int]]:
        # jscpd:ignore-end
        conn = await self._connect()
        target_lang = _infer_target_language(language)
        query = get_user_words_query(language, language, target_lang, word_type, limit, random)
        args: list[str | int] = [user_id, language]
        if word_type is not None:
            args.append(word_type)
        if limit is not None:
            args.append(limit)
        try:
            rows = await conn.fetch(query, *args)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        return [dict(row) for row in rows]

    async def increment_user_exercise_score(
        self,
        table: str,
        user_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> int:
        conn = await self._connect()
        try:
            row = await conn.fetchrow(
                increment_score_query(table),
                user_id,
                source_word_id,
                exercise_type,
                delta,
            )
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        return int(row["score"])  # type: ignore[index]

    async def get_user_exercise_scores(
        self,
        table: str,
        user_id: str,
        source_word_ids: list[int],
        exercise_types: list[str],
    ) -> list[dict[str, str | int]]:
        if not source_word_ids or not exercise_types:
            return []
        conn = await self._connect()
        try:
            rows = await conn.fetch(get_scores_query(table), user_id, source_word_ids, exercise_types)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        return [dict(row) for row in rows]


def _infer_target_language(source_language: str) -> str:
    """Infer the target language for translation lookups.

    With only two languages (nl, ru), the target is always the other one.
    """
    if source_language == "nl":
        return "ru"
    return "nl"
