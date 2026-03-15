from abc import ABC, abstractmethod
from datetime import datetime


class AbstractBackend(ABC):
    """Abstract base class defining the contract for all database operations."""

    @abstractmethod
    async def add_word(self, table: str, normalized_form: str, word_type: str) -> int | None:
        """Insert word if not exists, return row id."""

    @abstractmethod
    async def get_word(self, table: str, normalized_form: str) -> dict[str, str | int] | None:
        """Return row dict {id, normalized_form, word_type} or None."""

    @abstractmethod
    async def add_translation_link(self, table: str, source_id: int, target_id: int) -> None:
        """Create a translation link between source and target word ids."""

    @abstractmethod
    async def get_user_words(
        self,
        user_id: str,
        language: str,
        word_type: str | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[dict[str, str | int | datetime]]:
        """Return list of word row dicts for the given user and language."""

    @abstractmethod
    async def count_user_words(self, user_id: str, language: str, word_type: str | None = None) -> int:
        """Return total user-word associations for the given user and language."""

    @abstractmethod
    async def add_user_word(self, user_id: str, word_id: int, language: str) -> None:
        """Associate a word with a user."""

    @abstractmethod
    async def increment_user_exercise_score(
        self,
        table: str,
        user_id: str,
        source_word_id: int,
        delta: int,
    ) -> int:
        """Upsert exercise score by delta, return new score value."""

    @abstractmethod
    async def get_user_exercise_scores(
        self,
        table: str,
        user_id: str,
        source_word_ids: list[int],
    ) -> list[dict[str, str | int]]:
        """Return exercise score rows for the given user and words."""

    @abstractmethod
    async def check_event_applied(self, table: str, event_id: str) -> bool:
        """Check if event_id exists in the applied_events table."""

    @abstractmethod
    async def mark_event_applied(self, table: str, event_id: str) -> None:
        """Insert event_id into the applied_events table."""

    @abstractmethod
    async def apply_score_delta_atomic(
        self,
        score_table: str,
        events_table: str,
        user_id: str,
        event_id: str,
        source_word_id: int,
        delta: int,
    ) -> bool:
        """Atomically check-apply-mark a score delta in one transaction."""

    @abstractmethod
    async def create_tables(
        self,
        languages: list[str],
        pairs: list[tuple[str, str]],
        exercise_slugs: list[str],
    ) -> None:
        """Create all required database tables for the given languages and pairs."""

    @abstractmethod
    async def check_user_word_exists(self, user_id: str, source_word_id: int, language: str) -> bool:
        """Check if a source word is in the user's vocabulary."""

    @abstractmethod
    async def delete_user_word(self, user_id: str, source_word_id: int, language: str) -> None:
        """Delete the user's membership row for a source word."""

    @abstractmethod
    async def delete_user_exercise_score(self, table: str, user_id: str, source_word_id: int) -> None:
        """Delete the user's exercise score for a source word."""

    @abstractmethod
    async def upsert_word_details(
        self,
        table: str,
        source_word_id: int,
        word_type: str,
        schema_key: str,
        schema_version: int,
        payload: str,
    ) -> None:
        """Upsert detailed word record."""

    @abstractmethod
    async def get_word_details(self, table: str, source_word_id: int, word_type: str) -> dict[str, str | int] | None:
        """Get detailed word record by source_word_id and word_type."""

    @abstractmethod
    async def get_word_details_batch(
        self,
        table: str,
        source_word_ids_and_types: list[tuple[int, str]],
    ) -> list[dict[str, str | int]]:
        """Get detailed word records for multiple pairs."""
