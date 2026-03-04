from abc import ABC, abstractmethod


class AbstractBackend(ABC):
    """Abstract base class defining the contract for all database operations.

    Backend methods operate on primitives (str, int, dict), NOT on Word models.
    The DatabaseService layer handles conversion between Word model instances
    and backend primitives.
    """

    @abstractmethod
    async def add_word(
        self,
        table: str,
        normalized_form: str,
        word_type: str,
    ) -> int | None:
        """Insert word if not exists, return row id.

        Return None if already exists.
        """

    @abstractmethod
    async def get_word(
        self,
        table: str,
        normalized_form: str,
    ) -> dict[str, str | int] | None:
        """Return row dict {id, normalized_form, word_type} or None."""

    @abstractmethod
    async def add_translation_link(
        self,
        table: str,
        source_id: int,
        target_id: int,
    ) -> None:
        """Create a translation link between source and target word ids."""

    @abstractmethod
    async def get_user_words(
        self,
        user_id: str,
        language: str,
        word_type: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[dict[str, str | int]]:
        """Return list of word row dicts for the given user and language.

        Supports optional filtering by word_type, limiting result count,
        and random ordering.
        """

    @abstractmethod
    async def add_user_word(
        self,
        user_id: str,
        word_id: int,
        language: str,
    ) -> None:
        """Associate a word with a user. Idempotent (no error if already exists)."""

    @abstractmethod
    async def increment_user_exercise_score(
        self,
        table: str,
        user_id: str,
        source_word_id: int,
        exercise_type: str,
        delta: int,
    ) -> int:
        """Upsert exercise score by delta, return new score value."""

    @abstractmethod
    async def get_user_exercise_scores(
        self,
        table: str,
        user_id: str,
        source_word_ids: list[int],
        exercise_types: list[str],
    ) -> list[dict[str, str | int]]:
        """Return exercise score rows for the given user, words, and exercise types."""

    @abstractmethod
    async def create_tables(
        self,
        languages: list[str],
        pairs: list[tuple[str, str]],
    ) -> None:
        """Create all required database tables for the given languages and pairs.

        Uses IF NOT EXISTS semantics — safe to call multiple times.
        """
