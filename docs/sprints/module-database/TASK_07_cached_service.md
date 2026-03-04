---
Task ID: `T7`
Title: `Implement CachedDatabaseService caching wrapper`
Sprint: `2026-03-04_database`
Module: `database`
Depends on: `T6`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

A `CachedDatabaseService` class exists that wraps `DatabaseService` with an in-memory LRU cache for `get_words()` results. Repeated reads of the same query are served from cache, reducing Neon round-trips. Cache is invalidated on `add_words()` calls.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` -- NFR3 (local caching layer)
- Architecture: `nl_processing/database/docs/architecture_database.md` -- "Local Caching Layer" section
- Product brief: `nl_processing/database/docs/product-brief-database-2026-03-02.md` -- scope item 9

## Preconditions

- T6 completed: `DatabaseService` exists with `add_words()` and `get_words()`.

## Non-goals

- Distributed caching or external cache infrastructure
- TTL-based expiration (LRU is sufficient for v1)
- Caching at the backend level (cache is at the service level)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `nl_processing/database/service.py` -- add `CachedDatabaseService` class (if file has room under 200 lines)
- OR `nl_processing/database/cached_service.py` -- create new file (if `service.py` is near 200 lines)

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/core/` -- core package
- `nl_processing/database/backend/` -- backend layer
- Any test files
- Other modules

**Test scope:**
- No automated tests in this task. Covered by unit tests in T9.

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` -- add class (preferred) OR
- `nl_processing/database/cached_service.py` -- new file (if needed for 200-line limit)

## Dependencies and sequencing notes

- Depends on T6 for `DatabaseService`.
- Can be done in parallel with T8, T9, T12 (after T6).
- Unit tests in T9 will test cache behavior.

## Third-party / library research (mandatory for any external dependency)

- **Library**: Python `functools.lru_cache` (stdlib)
  - Not directly usable for async methods. **Not chosen.**
- **Library**: Python `dict` as simple cache (stdlib)
  - Simple `dict[str, list[WordPair]]` keyed by a hash of query parameters.
  - Manual LRU via `collections.OrderedDict` or size-limited dict.
  - **Chosen approach**: Simple dict-based cache with max-size eviction.

## Implementation steps (developer-facing)

### 1. Check `service.py` line count

If `service.py` is under ~160 lines after T6, add `CachedDatabaseService` to the same file.
If it's close to 200 lines, create `nl_processing/database/cached_service.py`.

### 2. Implement `CachedDatabaseService`

```python
from nl_processing.core.models import PartOfSpeech, Word
from nl_processing.database.models import AddWordsResult, WordPair
from nl_processing.database.service import DatabaseService


class CachedDatabaseService:
    """Caching wrapper around DatabaseService.

    Maintains an in-memory LRU cache of get_words() results.
    Cache is invalidated when add_words() is called.
    """

    def __init__(
        self,
        user_id: str,
        *,
        max_cache_size: int = 128,
        **kwargs: object,
    ) -> None:
        self._service = DatabaseService(user_id=user_id, **kwargs)
        self._cache: dict[str, list[WordPair]] = {}
        self._max_cache_size = max_cache_size

    @staticmethod
    def _cache_key(
        word_type: PartOfSpeech | None,
        limit: int | None,
        random: bool,
    ) -> str:
        """Generate a cache key from query parameters."""
        return f"{word_type}:{limit}:{random}"

    async def add_words(self, words: list[Word]) -> AddWordsResult:
        """Add words and invalidate the cache."""
        result = await self._service.add_words(words)
        self._cache.clear()  # Invalidate all cached results
        return result

    async def get_words(
        self,
        *,
        word_type: PartOfSpeech | None = None,
        limit: int | None = None,
        random: bool = False,
    ) -> list[WordPair]:
        """Get words, serving from cache if available."""
        # random queries bypass cache (results differ each call)
        if random:
            return await self._service.get_words(
                word_type=word_type, limit=limit, random=random
            )

        key = self._cache_key(word_type, limit, random)
        if key in self._cache:
            return self._cache[key]

        result = await self._service.get_words(
            word_type=word_type, limit=limit, random=random
        )

        # Evict oldest entry if cache is full
        if len(self._cache) >= self._max_cache_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = result
        return result

    @classmethod
    async def create_tables(cls) -> None:
        """Delegate to DatabaseService.create_tables()."""
        await DatabaseService.create_tables()
```

### 3. Key design decisions

- **Cache invalidation on write**: `add_words()` clears the entire cache. This is simple and correct -- new words may affect any query result.
- **Random queries bypass cache**: `random=True` queries return different results each call, so caching would be incorrect.
- **LRU eviction**: When cache exceeds `max_cache_size`, the oldest entry is evicted. Python 3.7+ dicts maintain insertion order.
- **Per-instance cache**: Each `CachedDatabaseService` instance has its own cache. No cross-instance sharing.
- **Cache is not persistent**: Lost on process restart (architecture decision).

### 4. Verify file is under 200 lines

### 5. Run `make check`

## Production safety constraints (mandatory)

- No production impact. In-memory cache only.
- No database operations added beyond what `DatabaseService` already does.

## Anti-disaster constraints (mandatory)

- Delegates to `DatabaseService` for all actual DB operations.
- Cache is a simple dict -- no external dependencies.
- No new libraries introduced.

## Error handling + correctness rules (mandatory)

- All exceptions from `DatabaseService` propagate through unchanged.
- Cache miss triggers a real DB query -- no "return default" to mask failures.
- No error silencing.

## Zero legacy tolerance rule (mandatory)

- No legacy code affected.

## Acceptance criteria (testable)

1. `CachedDatabaseService` class exists (in `service.py` or `cached_service.py`)
2. `add_words()` delegates to `DatabaseService.add_words()` and clears cache
3. `get_words()` returns cached results for repeated identical queries
4. `get_words(random=True)` bypasses cache
5. Cache evicts oldest entry when `max_cache_size` is exceeded
6. `create_tables()` delegates to `DatabaseService.create_tables()`
7. File under 200 lines
8. `make check` passes 100% green

## Verification / quality gates

- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Import works: `from nl_processing.database.service import CachedDatabaseService` (or from `cached_service`)
- [ ] `make check` passes 100% green

## Edge cases

- Cache with 0 entries: first `get_words()` call always goes to DB.
- `add_words([])`: still clears cache (conservative approach).
- Multiple sequential `get_words()` with same params: first hits DB, subsequent from cache.
- `max_cache_size=1`: only one query cached at a time.

## Notes / risks

- **Decision made autonomously**: Using `dict` with insertion-order eviction instead of `collections.OrderedDict`. Python 3.7+ dicts maintain insertion order, making `OrderedDict` unnecessary.
- **Decision made autonomously**: `max_cache_size=128` default. Appropriate for typical usage patterns.
- **Risk**: If `service.py` exceeds 200 lines, `CachedDatabaseService` must go in a separate file. The developer should check the line count before deciding.
