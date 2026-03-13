"""NeonBackend asyncpg implementation for Neon PostgreSQL."""

from datetime import datetime

import asyncpg

from nl_processing.database.backend._neon_delete import (
    check_word_exists,
    delete_exercise_score,
    delete_word_membership,
)
from nl_processing.database.backend._neon_detailed import (
    get_details,
    get_details_batch,
    upsert_details,
)
from nl_processing.database.backend._neon_exercise import (
    atomic_apply_delta,
    check_event,
    create_exercise_tables,
    get_scores,
    increment_score,
    mark_event,
)
from nl_processing.database.backend._neon_users import (
    add_translation_link as add_translation_link_impl,
    add_user_word as add_user_word_impl,
    get_user_words as get_user_words_impl,
)
from nl_processing.database.backend._neon_words import (
    add_word as add_word_impl,
    count_user_words as count_user_words_impl,
    get_word as get_word_impl,
)
from nl_processing.database.backend._queries import (
    CREATE_USER_WORDS,
    create_translations_table,
    create_words_table,
)
from nl_processing.database.backend._queries_detailed import create_word_details_table
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
        if self._connection is None:
            try:
                self._connection = await asyncpg.connect(dsn=self._database_url)
                _logger.info("Connected to Neon PostgreSQL")
            except asyncpg.PostgresError as exc:
                raise DatabaseError(str(exc)) from exc
            except OSError as exc:
                raise DatabaseError(str(exc)) from exc
        if self._connection is None:
            raise DatabaseError("Database connection was not initialized")
        return self._connection

    async def create_tables(
        self, languages: list[str], pairs: list[tuple[str, str]], exercise_slugs: list[str]
    ) -> None:
        conn = await self._connect()
        try:
            for lang in languages:
                await conn.execute(create_words_table(lang))
            for src, tgt in pairs:
                await conn.execute(create_translations_table(src, tgt))
            await conn.execute(CREATE_USER_WORDS)
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        await create_exercise_tables(conn, pairs, exercise_slugs)
        # Create detailed word tables
        try:
            for src, tgt in pairs:
                await conn.execute(create_word_details_table(src, tgt))
        except asyncpg.PostgresError as exc:
            raise DatabaseError(str(exc)) from exc
        _logger.info("Created tables for languages=%s pairs=%s", languages, pairs)

    async def add_word(self, table: str, normalized_form: str, word_type: str) -> int | None:
        return await add_word_impl(await self._connect(), table, normalized_form, word_type)

    async def get_word(self, table: str, normalized_form: str) -> dict[str, str | int] | None:
        return await get_word_impl(await self._connect(), table, normalized_form)

    async def add_translation_link(self, table: str, source_id: int, target_id: int) -> None:
        await add_translation_link_impl(await self._connect(), table, source_id, target_id)

    async def add_user_word(self, user_id: str, word_id: int, language: str) -> None:
        await add_user_word_impl(await self._connect(), user_id, word_id, language)

    # jscpd:ignore-start — method signature must match AbstractBackend ABC
    async def get_user_words(
        self,
        user_id: str,
        language: str,
        word_type: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[dict[str, str | int | datetime]]:
        # jscpd:ignore-end
        conn = await self._connect()
        return await get_user_words_impl(conn, user_id, language, word_type, limit, random)

    async def count_user_words(self, user_id: str, language: str, word_type: str | None = None) -> int:
        return await count_user_words_impl(await self._connect(), user_id, language, word_type)

    async def increment_user_exercise_score(self, table: str, user_id: str, source_word_id: int, delta: int) -> int:
        conn = await self._connect()
        return await increment_score(conn, table, user_id, source_word_id, delta)

    async def get_user_exercise_scores(
        self, table: str, user_id: str, source_word_ids: list[int]
    ) -> list[dict[str, str | int]]:
        conn = await self._connect()
        return await get_scores(conn, table, user_id, source_word_ids)

    async def check_event_applied(self, table: str, event_id: str) -> bool:
        conn = await self._connect()
        return await check_event(conn, table, event_id)

    async def mark_event_applied(self, table: str, event_id: str) -> None:
        conn = await self._connect()
        await mark_event(conn, table, event_id)

    async def apply_score_delta_atomic(
        self, score_table: str, events_table: str,
        user_id: str, event_id: str, source_word_id: int, delta: int,
    ) -> bool:  # fmt: skip
        conn = await self._connect()
        return await atomic_apply_delta(conn, score_table, events_table, user_id, event_id, source_word_id, delta)

    async def check_user_word_exists(
        self,
        user_id: str,
        source_word_id: int,
        language: str,
    ) -> bool:
        conn = await self._connect()
        return await check_word_exists(conn, user_id, source_word_id, language)

    async def delete_user_word(
        self,
        user_id: str,
        source_word_id: int,
        language: str,
    ) -> None:
        conn = await self._connect()
        await delete_word_membership(conn, user_id, source_word_id, language)

    async def delete_user_exercise_score(
        self,
        table: str,
        user_id: str,
        source_word_id: int,
    ) -> None:
        conn = await self._connect()
        await delete_exercise_score(conn, table, user_id, source_word_id)

    async def upsert_word_details(
        self,
        table: str,
        source_word_id: int,
        word_type: str,
        schema_key: str,
        schema_version: int,
        payload: str,
    ) -> None:
        conn = await self._connect()
        await upsert_details(conn, table, source_word_id, word_type, schema_key, schema_version, payload)

    async def get_word_details(
        self,
        table: str,
        source_word_id: int,
        word_type: str,
    ) -> dict[str, str | int] | None:
        conn = await self._connect()
        return await get_details(conn, table, source_word_id, word_type)

    async def get_word_details_batch(
        self,
        table: str,
        source_word_ids_and_types: list[tuple[int, str]],
    ) -> list[dict[str, str | int]]:
        conn = await self._connect()
        return await get_details_batch(conn, table, source_word_ids_and_types)
