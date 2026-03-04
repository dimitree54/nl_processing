"""CachedDatabaseService — wraps DatabaseService with in-memory LRU cache."""

from nl_processing.core.models import Language, PartOfSpeech, Word
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.database.service import DatabaseService


class CachedDatabaseService:
    """Wraps DatabaseService with an in-memory LRU cache for get_words."""

    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
        cache_max_size: int = 128,
    ) -> None:
        self._inner = DatabaseService(
            user_id=user_id,
            source_language=source_language,
            target_language=target_language,
        )
        self._cache: dict[tuple[str | None, int | None, bool], list[WordPair]] = {}
        self._cache_max_size = cache_max_size
        self._cache_order: list[tuple[str | None, int | None, bool]] = []

    async def add_words(self, words: list[Word]) -> AddWordsResult:
        """Delegate to inner service and clear the cache."""
        result = await self._inner.add_words(words)
        self._cache.clear()
        self._cache_order.clear()
        return result

    async def get_words(
        self,
        *,
        word_type: PartOfSpeech | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Return word pairs, serving from cache when possible.

        Random queries and zero-size caches bypass the cache entirely.
        """
        if random or self._cache_max_size <= 0:
            return await self._inner.get_words(
                word_type=word_type,
                limit=limit,
                random=random,
            )

        key = (word_type.value if word_type else None, limit, False)
        if key in self._cache:
            self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]

        result = await self._inner.get_words(
            word_type=word_type,
            limit=limit,
            random=random,
        )
        self._cache[key] = result
        self._cache_order.append(key)
        while len(self._cache_order) > self._cache_max_size:
            oldest = self._cache_order.pop(0)
            self._cache.pop(oldest, None)
        return result

    @classmethod
    async def create_tables(cls) -> None:
        """Delegate to DatabaseService.create_tables."""
        await DatabaseService.create_tables()
