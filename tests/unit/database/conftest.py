"""Shared fixtures for database unit tests — MockBackend and service factories."""

import random as stdlib_random

import pytest

from nl_processing.core.models import Language, Word
from nl_processing.database.backend.abstract import AbstractBackend
from nl_processing.database.cached_service import CachedDatabaseService
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.database.service import DatabaseService


class MockBackend(AbstractBackend):
    """In-memory backend that tracks words, links, user-words, and scores."""

    def __init__(self) -> None:
        self._next_id: dict[str, int] = {}
        self._words: dict[str, dict[str, dict[str, str | int]]] = {}
        self._links: list[tuple[str, int, int]] = []
        self._user_words: list[tuple[str, int, str]] = []
        self._scores: dict[tuple[str, str, int, str], int] = {}

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
    ) -> list[dict[str, str | int]]:
        # jscpd:ignore-end
        src_table = language
        tgt_lang = "ru" if language == "nl" else "nl"
        tgt_table = tgt_lang
        trans_table = f"{language}_{tgt_lang}"
        rows: list[dict[str, str | int]] = []
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

    async def increment_user_exercise_score(
        self, table: str, user_id: str, source_word_id: int, exercise_type: str, delta: int
    ) -> int:
        key = (table, user_id, source_word_id, exercise_type)
        self._scores[key] = self._scores.get(key, 0) + delta
        return self._scores[key]

    async def get_user_exercise_scores(
        self, table: str, user_id: str, source_word_ids: list[int], exercise_types: list[str]
    ) -> list[dict[str, str | int]]:
        if not source_word_ids or not exercise_types:
            return []
        result: list[dict[str, str | int]] = []
        for (tbl, uid, wid, etype), score in self._scores.items():
            if tbl == table and uid == user_id and wid in source_word_ids and etype in exercise_types:
                result.append({"source_word_id": wid, "exercise_type": etype, "score": score})
        return result

    async def create_tables(self, languages: list[str], pairs: list[tuple[str, str]]) -> None:
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
    def _build_joined_row(src: dict[str, str | int], tgt: dict[str, str | int]) -> dict[str, str | int]:
        return {
            "source_id": src["id"],
            "source_normalized_form": src["normalized_form"],
            "source_word_type": src["word_type"],
            "target_id": tgt["id"],
            "target_normalized_form": tgt["normalized_form"],
            "target_word_type": tgt["word_type"],
        }


class MockTranslator:
    """Fake translator that uppercases the normalized_form as 'translation'."""

    def __init__(self, target_language: Language) -> None:
        self._target = target_language

    async def translate(self, words: list[Word]) -> list[Word]:
        return [
            Word(normalized_form=w.normalized_form.upper(), word_type=w.word_type, language=self._target) for w in words
        ]


@pytest.fixture
def mock_backend() -> MockBackend:
    return MockBackend()


@pytest.fixture
def db_service(monkeypatch: pytest.MonkeyPatch, mock_backend: MockBackend) -> DatabaseService:
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    svc = DatabaseService(user_id="u1")
    svc._backend = mock_backend  # type: ignore[assignment]
    svc._translator = MockTranslator(target_language=Language.RU)  # type: ignore[assignment]
    return svc


@pytest.fixture
def cached_service(monkeypatch: pytest.MonkeyPatch, mock_backend: MockBackend) -> CachedDatabaseService:
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    svc = CachedDatabaseService(user_id="u1")
    svc._inner._backend = mock_backend  # type: ignore[assignment]
    svc._inner._translator = MockTranslator(target_language=Language.RU)  # type: ignore[assignment]
    return svc


@pytest.fixture
def progress_store(monkeypatch: pytest.MonkeyPatch, mock_backend: MockBackend) -> ExerciseProgressStore:
    monkeypatch.setenv("DATABASE_URL", "mock://test")
    store = ExerciseProgressStore(user_id="u1", source_language=Language.NL, target_language=Language.RU)
    store._backend = mock_backend  # type: ignore[assignment]
    return store
