"""MockBackend implementation for unit tests."""

from datetime import datetime, timezone
import random as stdlib_random

from nl_processing.database_core.backend.abstract import AbstractBackend


class MockBackend(AbstractBackend):
    """In-memory backend that tracks words, links, user-words, and scores."""

    def __init__(self) -> None:
        self._next_id: dict[str, int] = {}
        self._words: dict[str, dict[str, dict[str, str | int]]] = {}
        self._links: list[tuple[str, int, int]] = []
        self._user_words: list[tuple[str, int, str]] = []
        self._scores: dict[tuple[str, str, int], int] = {}
        self._applied_events: set[tuple[str, str]] = set()
        self._detailed_words: dict[tuple[str, int, str], dict[str, str | int]] = {}
        self.count_user_words_calls = 0

    def create_background_backend(self) -> AbstractBackend:
        """Reuse the in-memory backend during unit tests."""
        return self

    async def add_word(self, table: str, normalized_form: str, word_type: str) -> int | None:
        bucket = self._words.setdefault(table, {})
        if normalized_form in bucket:
            return None
        wid = self._next_id.get(table, 1)
        self._next_id[table] = wid + 1
        bucket[normalized_form] = {"id": wid, "normalized_form": normalized_form, "word_type": word_type}
        return wid

    async def get_word(self, table: str, normalized_form: str) -> dict[str, str | int] | None:
        return self._words.get(table, {}).get(normalized_form)

    async def add_translation_link(self, table: str, source_id: int, target_id: int) -> None:
        self._links.append((table, source_id, target_id))

    async def add_user_word(self, user_id: str, word_id: int, language: str) -> None:
        entry = (user_id, word_id, language)
        if entry not in self._user_words:
            self._user_words.append(entry)

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
        src_table = language
        tgt_lang = "ru" if language == "nl" else "nl"
        tgt_table = tgt_lang
        trans_table = f"{language}_{tgt_lang}"
        rows: list[dict[str, str | int | datetime]] = []
        for uid, wid, lang in self._user_words:
            if uid != user_id or lang != language:
                continue
            src = self._find_word_by_id(src_table, wid)
            if src is None:
                continue
            if word_type is not None and src["word_type"] != word_type:
                continue
            tid = self._find_target_id(trans_table, wid)
            if tid is None:
                continue
            tgt = self._find_word_by_id(tgt_table, tid)
            if tgt is None:
                continue
            rows.append(self._build_joined_row(src, tgt))
        if random:
            stdlib_random.shuffle(rows)
        if limit is not None:
            rows = rows[:limit]
        return rows

    async def count_user_words(self, user_id: str, language: str, word_type: str | None = None) -> int:
        self.count_user_words_calls += 1
        count = 0
        for uid, wid, lang in self._user_words:
            if uid != user_id or lang != language:
                continue
            src = self._find_word_by_id(language, wid)
            if src is None:
                continue
            if word_type is not None and src["word_type"] != word_type:
                continue
            count += 1
        return count

    async def increment_user_exercise_score(
        self,
        table: str,
        user_id: str,
        source_word_id: int,
        delta: int,
    ) -> int:
        key = (table, user_id, source_word_id)
        self._scores[key] = self._scores.get(key, 0) + delta
        return self._scores[key]

    async def get_user_exercise_scores(
        self, table: str, user_id: str, source_word_ids: list[int]
    ) -> list[dict[str, str | int]]:
        if not source_word_ids:
            return []
        result: list[dict[str, str | int]] = []
        for (tbl, uid, wid), score in self._scores.items():
            if tbl == table and uid == user_id and wid in source_word_ids:
                result.append({"source_word_id": wid, "score": score})
        return result

    async def apply_score_delta_atomic(
        self, score_table: str, events_table: str, user_id: str, event_id: str, source_word_id: int, delta: int
    ) -> bool:
        if (events_table, event_id) in self._applied_events:
            return False
        key = (score_table, user_id, source_word_id)
        self._scores[key] = self._scores.get(key, 0) + delta
        self._applied_events.add((events_table, event_id))
        return True

    async def create_tables(
        self, languages: list[str], pairs: list[tuple[str, str]], exercise_slugs: list[str]
    ) -> None:
        pass

    # ---- helpers ----
    def _find_word_by_id(self, table: str, wid: int) -> dict[str, str | int] | None:
        for row in self._words.get(table, {}).values():
            if row["id"] == wid:
                return row
        return None

    def _find_target_id(self, trans_table: str, source_id: int) -> int | None:
        for tbl, sid, tid in self._links:
            if tbl == trans_table and sid == source_id:
                return tid
        return None

    @staticmethod
    def _build_joined_row(src: dict[str, str | int], tgt: dict[str, str | int]) -> dict[str, str | int | datetime]:
        return {
            "source_id": src["id"],
            "source_normalized_form": src["normalized_form"],
            "source_word_type": src["word_type"],
            "target_id": tgt["id"],
            "target_normalized_form": tgt["normalized_form"],
            "target_word_type": tgt["word_type"],
            "added_at": datetime.now(tz=timezone.utc),
        }

    async def check_user_word_exists(self, user_id: str, source_word_id: int, language: str) -> bool:
        for uid, wid, lang in self._user_words:
            if uid == user_id and wid == source_word_id and lang == language:
                return True
        return False

    async def delete_user_word(self, user_id: str, source_word_id: int, language: str) -> None:
        self._user_words = [
            (u, w, l) for u, w, l in self._user_words if not (u == user_id and w == source_word_id and l == language)
        ]

    async def delete_user_exercise_score(self, table: str, user_id: str, source_word_id: int) -> None:
        key = (table, user_id, source_word_id)
        self._scores.pop(key, None)

    async def upsert_word_details(
        self, table: str, source_word_id: int, word_type: str, schema_key: str, schema_version: int, payload: str
    ) -> None:
        self._detailed_words[(table, source_word_id, word_type)] = {
            "source_word_id": source_word_id,
            "word_type": word_type,
            "schema_key": schema_key,
            "schema_version": schema_version,
            "payload": payload,
        }

    async def get_word_details(self, table: str, source_word_id: int, word_type: str) -> dict[str, str | int] | None:
        return self._detailed_words.get((table, source_word_id, word_type))

    async def get_word_details_batch(
        self, table: str, source_word_ids_and_types: list[tuple[int, str]]
    ) -> list[dict[str, str | int]]:
        return [
            self._detailed_words[key]
            for key in [(table, wid, wtype) for wid, wtype in source_word_ids_and_types]
            if key in self._detailed_words
        ]
