---
Task ID: `T7`
Title: `Implement CachedDatabaseService`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T5`
Parallelizable: `yes, with T6 and T8`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`CachedDatabaseService` wraps `DatabaseService` with an in-memory LRU cache for `get_words` results, reducing read latency for repeated access patterns.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — NFR3 (local caching layer)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Decision: Local Caching Layer (CachedDatabaseService)

## Preconditions

- T5 complete (DatabaseService exists)
- T2 complete (models exist)

## Non-goals

- No cache invalidation beyond LRU eviction
- No distributed caching
- No persistence of cache

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/service.py` — add `CachedDatabaseService` class (same file as `DatabaseService` per architecture)

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/__init__.py`
- Any other module's code or tests

**Test scope:**

- No new tests in this task (tested as part of T9)
- `make check` must pass

## Touched surface (expected files / modules)

- `nl_processing/database/service.py` (add class)

## Dependencies and sequencing notes

- Depends on T5 (DatabaseService exists in service.py)
- Can run in parallel with T6 and T8
- T9 (unit tests) covers this

## Third-party / library research (mandatory for any external dependency)

- **Library**: Python `functools.lru_cache` or manual dict-based cache (stdlib)
  - **Docs**: https://docs.python.org/3.12/library/functools.html#functools.lru_cache
  - Note: `lru_cache` doesn't work with async methods. Use a manual dict-based approach with max size eviction.

## Implementation steps (developer-facing)

1. **Add `CachedDatabaseService` to `nl_processing/database/service.py`:**

2. **Design:**
   - Wraps a `DatabaseService` instance (composition, not inheritance)
   - Constructor: `__init__(self, *, user_id, source_language, target_language, cache_max_size: int = 128)`
   - Creates internal `DatabaseService` with same params
   - Maintains `_cache: dict` keyed by `(word_type, limit, random)` tuples for `get_words`

3. **`add_words`**: Delegates to inner `DatabaseService.add_words()`. Clears the cache (new words invalidate cached results).

4. **`get_words`**: Check cache with key `(word_type, limit, random)`. If hit, return cached result. If miss, call inner service, store in cache (evict oldest if cache exceeds `cache_max_size`), return result.

5. **`create_tables`**: Delegates directly to `DatabaseService.create_tables()` (class method).

6. **200-line awareness**: service.py now contains TWO classes. The file had `DatabaseService` from T5. Adding `CachedDatabaseService` (small class, ~30-40 lines) should keep total under 200 lines. If tight, extract `CachedDatabaseService` into a separate `cached_service.py` file.

7. Run `make check`.

## Production safety constraints (mandatory)

- **Database operations**: None — delegates to DatabaseService.
- **Resource isolation**: N/A — in-memory cache only.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Wraps existing DatabaseService — no duplication.
- **Correct file locations**: `service.py` per architecture doc.

## Error handling + correctness rules (mandatory)

- No error swallowing — all exceptions from inner service propagate unchanged.
- Cache misses result in real DB calls — no stale-data-as-fallback.

## Zero legacy tolerance rule (mandatory)

- No old code paths.

## Acceptance criteria (testable)

1. `CachedDatabaseService` exists in `nl_processing/database/service.py`.
2. It wraps `DatabaseService` (composition).
3. `get_words` caches results keyed by parameters.
4. `add_words` clears the cache.
5. Cache has configurable max size with LRU eviction.
6. All public methods match `DatabaseService` interface (async).
7. `service.py` remains under 200 lines (or split into two files).
8. `make check` passes.

## Verification / quality gates

- [ ] CachedDatabaseService implemented
- [ ] Cache hit/miss logic correct
- [ ] Cache cleared on add_words
- [ ] File under 200 lines
- [ ] `make check` passes

## Edge cases

- Cache key with `random=True` — probably should NOT cache random results (different random set each time). Consider: cache only when `random=False`.
- `cache_max_size=0` — disable caching, delegate everything.
- Thread safety — not required (per-instance, single-user).

## Notes / risks

- **Risk**: Caching `random=True` results returns the same "random" set repeatedly.
  - **Mitigation**: Do NOT cache when `random=True`. Only cache deterministic queries.
