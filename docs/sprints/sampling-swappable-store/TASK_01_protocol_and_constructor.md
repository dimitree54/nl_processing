---
Task ID: T1
Title: Add `ScoredPairProvider` Protocol and modify `WordSampler` constructor for data source injection
Sprint: 2026-03-08_sampling-swappable-store
Module: sampling
Depends on: —
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

After this task, `WordSampler` accepts an optional `scored_store` parameter conforming to the `ScoredPairProvider` Protocol. When provided, the sampler uses it instead of constructing `ExerciseProgressStore`. All existing tests continue to pass (backward compatibility). New tests verify: (1) the injection path works, (2) `MockProgressStore` satisfies `ScoredPairProvider` at runtime, and (3) `DatabaseCacheService` satisfies `ScoredPairProvider` at runtime.

## Context (contract mapping)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` — FR21 (optional `scored_store` param), FR22 (`ScoredPairProvider` Protocol), FR23 (both stores satisfy it structurally), FR24 (backward compat), FR25 (no `DatabaseCacheService` import in sampler)
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` — "Protocol-Based Data Source Injection" section
- Existing code: `nl_processing/sampling/service.py` (current `WordSampler`), `tests/unit/sampling/conftest.py` (current fixtures)

## Preconditions

- Current code and tests pass (`make check` green)
- `nl_processing/sampling/service.py` is at 105 lines

## Non-goals

- Modifying `ExerciseProgressStore` or `DatabaseCacheService`
- Adding integration or E2E tests
- Updating docs (already done)
- Updating vulture whitelist (T2)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/sampling/service.py` — add Protocol, modify constructor
- `tests/unit/sampling/conftest.py` — update fixtures
- `tests/unit/sampling/test_sampling_weights.py` — add new tests

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/` — no changes to `ExerciseProgressStore`
- `nl_processing/database_cache/` — no changes to `DatabaseCacheService`
- `nl_processing/core/` — no changes
- Any other module's code or tests
- `vulture_whitelist.py` (that's T2)
- `nl_processing/sampling/docs/` — docs already finalized

**Test scope:**
- Tests go in: `tests/unit/sampling/`
- Test command: `uv run pytest tests/unit/sampling/ -x -v`
- NEVER run the full test suite or tests from other modules (except via `make check` at the end)

## Touched surface (expected files / modules)

- `nl_processing/sampling/service.py` (~13 lines added/changed)
- `tests/unit/sampling/conftest.py` (~15 lines added/changed)
- `tests/unit/sampling/test_sampling_weights.py` (~30 lines added)

## Dependencies and sequencing notes

- No dependencies — this is the first task
- T2 depends on this task (Protocol must exist before whitelisting)

## Third-party / library research (mandatory for any external dependency)

- **`typing.Protocol`**: Built-in to Python 3.12+ (no external dependency).
  - Documentation: https://docs.python.org/3.12/library/typing.html#typing.Protocol
  - `@runtime_checkable` decorator: https://docs.python.org/3.12/library/typing.html#typing.runtime_checkable
  - Usage: Decorate a Protocol class with `@runtime_checkable` to enable `isinstance()` checks at runtime. Without it, `isinstance()` raises `TypeError`.
  - Gotcha: `@runtime_checkable` only checks that the required methods exist as attributes — it does NOT validate signatures or return types at runtime. This is sufficient for our conformance tests (we want to verify structural presence, not full type checking).
  - Example:
    ```python
    from typing import Protocol, runtime_checkable

    @runtime_checkable
    class ScoredPairProvider(Protocol):
        async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...

    # isinstance(obj, ScoredPairProvider) returns True if obj has the method
    ```

## Implementation steps (developer-facing)

### Step 1: Add `ScoredPairProvider` Protocol to `service.py`

Open `nl_processing/sampling/service.py`.

1. Add `from typing import Protocol, runtime_checkable` to the imports.

2. Add the Protocol class **before** `WordSampler`, after the imports:

```python
@runtime_checkable
class ScoredPairProvider(Protocol):
    """Data source that provides scored word pairs for sampling."""

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...
```

### Step 2: Modify `WordSampler.__init__` to accept optional `scored_store`

In the same file, modify `WordSampler.__init__`:

1. Add `scored_store: ScoredPairProvider | None = None` as a keyword argument (after `positive_balance_weight`).

2. Replace the unconditional `ExerciseProgressStore` construction with:
```python
if scored_store is not None:
    self._progress_store: ScoredPairProvider = scored_store
else:
    self._progress_store = ExerciseProgressStore(
        user_id=user_id,
        source_language=source_language,
        target_language=target_language,
        exercise_types=exercise_types,
    )
```

3. The type annotation `self._progress_store: ScoredPairProvider` ensures the attribute is typed as the Protocol, not the concrete class. This is the only type annotation change needed — the rest of the class uses `self._progress_store.get_word_pairs_with_scores()` which is defined on the Protocol.

### Step 3: Verify `service.py` stays under 200 lines

Current: 105 lines. Added: ~13 lines (2 imports, 5 Protocol, 6 constructor changes). Expected total: ~118 lines. Well under 200.

### Step 4: Update `conftest.py` — add injection-path fixture

Open `tests/unit/sampling/conftest.py`.

1. Add a new fixture that creates a `WordSampler` using the injection path:

```python
@pytest.fixture
def sampler_injected() -> WordSampler:
    """Create a WordSampler with an injected mock store (no DATABASE_URL needed)."""
    mock_store = MockProgressStore([])
    return WordSampler(
        user_id="u1",
        exercise_types=["flashcard"],
        scored_store=mock_store,
    )
```

Note: This fixture does NOT need `monkeypatch.setenv("DATABASE_URL", ...)` because when `scored_store` is provided, `ExerciseProgressStore` is never constructed, so `DATABASE_URL` is never read. This is a key verification of the injection path.

### Step 5: Update `conftest.py` — update `patch_store` helper to use `ScoredPairProvider` type

The existing `patch_store` function has `# type: ignore[assignment]` because it assigns a `MockProgressStore` to `_progress_store` which was typed as `ExerciseProgressStore`. After this change, `_progress_store` is typed as `ScoredPairProvider`, and `MockProgressStore` satisfies the Protocol — so the `# type: ignore` can be removed:

```python
def patch_store(sampler: WordSampler, scored_pairs: list[ScoredWordPair]) -> None:
    """Replace the sampler's progress store with a mock returning the given pairs."""
    sampler._progress_store = MockProgressStore(scored_pairs)
```

### Step 6: Add tests to `test_sampling_weights.py`

Open `tests/unit/sampling/test_sampling_weights.py`.

Add three new tests at the end of the file:

**Test 1: Injection path works — no `DATABASE_URL` needed**

```python
def test_constructor_with_scored_store_skips_env(sampler_injected: WordSampler) -> None:
    """When scored_store is provided, DATABASE_URL is not required."""
    # sampler_injected fixture creates a sampler WITHOUT setting DATABASE_URL.
    # If construction reached ExerciseProgressStore, it would raise ConfigurationError.
    assert sampler_injected._positive_balance_weight == 0.01
```

**Test 2: `MockProgressStore` satisfies `ScoredPairProvider` at runtime**

```python
def test_mock_progress_store_satisfies_protocol() -> None:
    """MockProgressStore structurally satisfies ScoredPairProvider."""
    from nl_processing.sampling.service import ScoredPairProvider
    from tests.unit.sampling.conftest import MockProgressStore

    mock = MockProgressStore([])
    assert isinstance(mock, ScoredPairProvider)
```

**Test 3: `DatabaseCacheService` satisfies `ScoredPairProvider` at runtime**

```python
def test_database_cache_service_satisfies_protocol() -> None:
    """DatabaseCacheService structurally satisfies ScoredPairProvider."""
    from nl_processing.database_cache.service import DatabaseCacheService
    from nl_processing.sampling.service import ScoredPairProvider

    assert issubclass(DatabaseCacheService, ScoredPairProvider)
```

Note: We use `issubclass` for `DatabaseCacheService` instead of `isinstance` because constructing a `DatabaseCacheService` requires real parameters. `issubclass` with `@runtime_checkable` Protocol checks method presence on the class itself.

**Test 4: Injection-path sampling works end-to-end**

```python
@pytest.mark.asyncio
async def test_sample_via_injected_store() -> None:
    """Sampling works when store is injected via scored_store parameter."""
    from tests.unit.sampling.conftest import MockProgressStore, make_scored_pair

    pairs = [make_scored_pair(f"w{i}", f"t{i}", scores={"flashcard": 0}) for i in range(5)]
    mock_store = MockProgressStore(pairs)
    ws = WordSampler(
        user_id="u1",
        exercise_types=["flashcard"],
        scored_store=mock_store,
    )
    result = await ws.sample(3)
    assert len(result) == 3
```

### Step 7: Run tests

```bash
uv run pytest tests/unit/sampling/ -x -v
```

All existing tests must pass. All new tests must pass.

### Step 8: Verify no import of `DatabaseCacheService` in `service.py`

Confirm that `nl_processing/sampling/service.py` does NOT import `DatabaseCacheService` (FR25). The Protocol enables loose coupling — only the test file imports `DatabaseCacheService` for conformance checking.

### Step 9: Run unit tests one final time

```bash
uv run pytest tests/unit/sampling/ -x -v
```

Note: Do NOT run `make check` yet — vulture will flag `ScoredPairProvider` as unused (T2 fixes this).

## Production safety constraints (mandatory)

- **Database operations**: None. All tests use mock stores. The `sampler` fixture uses a dummy `DATABASE_URL` that never connects. The `sampler_injected` fixture doesn't need `DATABASE_URL` at all.
- **Resource isolation**: N/A — no files, ports, sockets, or databases used.
- **Migration preparation**: N/A — no data model changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing `WordSampler` and `MockProgressStore`. No new files created.
- **Correct libraries only**: `typing.Protocol` and `typing.runtime_checkable` are Python 3.12+ stdlib. No new dependencies.
- **Correct file locations**: All changes in existing files within module and test boundaries.
- **No regressions**: Existing `sampler` fixture and all existing tests are preserved unchanged. New tests are additive.
- **Follow UX/spec**: Constructor signature matches PRD FR21–FR22 and architecture spec exactly.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: No try/catch added. If `scored_store` doesn't conform to Protocol, Python's type checker catches it statically. Runtime conformance is tested explicitly.
- **No mock fallbacks**: The `scored_store=None` default triggers the real `ExerciseProgressStore` construction — it's not a "mock fallback", it's the documented backward-compat behavior (FR24).

## Zero legacy tolerance rule (mandatory)

After implementing this task:

- Remove the `# type: ignore[assignment]` from `patch_store` in `conftest.py` — no longer needed since `_progress_store` is now typed as `ScoredPairProvider` which `MockProgressStore` satisfies.
- No dead code paths — the `if/else` in the constructor is the documented behavior, not a legacy toggle.

## Acceptance criteria (testable)

1. `ScoredPairProvider` Protocol exists in `nl_processing/sampling/service.py` with `@runtime_checkable` decorator and `async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]` method.
2. `WordSampler.__init__` accepts `scored_store: ScoredPairProvider | None = None` as a keyword argument.
3. When `scored_store` is provided, `self._progress_store` is set to the provided store (no `ExerciseProgressStore` construction, no `DATABASE_URL` needed).
4. When `scored_store` is `None` (default), `ExerciseProgressStore` is constructed as before (backward compatible).
5. `self._progress_store` is typed as `ScoredPairProvider` (not `ExerciseProgressStore`).
6. `nl_processing/sampling/service.py` does NOT import `DatabaseCacheService` (FR25).
7. `isinstance(MockProgressStore([]), ScoredPairProvider)` returns `True`.
8. `issubclass(DatabaseCacheService, ScoredPairProvider)` returns `True`.
9. All existing tests in `tests/unit/sampling/` continue to pass without modification.
10. `nl_processing/sampling/service.py` remains ≤ 200 lines.
11. `uv run pytest tests/unit/sampling/ -x -v` passes.

## Verification / quality gates

- [ ] Unit tests added for Protocol conformance (MockProgressStore, DatabaseCacheService)
- [ ] Unit test added for injection path (no DATABASE_URL needed)
- [ ] Unit test added for injection-path sampling (end-to-end mock)
- [ ] All existing tests pass unchanged
- [ ] `uv run pytest tests/unit/sampling/ -x -v` passes
- [ ] `nl_processing/sampling/service.py` ≤ 200 lines
- [ ] No `DatabaseCacheService` import in `service.py`
- [ ] `# type: ignore[assignment]` removed from `patch_store`

## Edge cases

- **`scored_store` is provided but does not satisfy Protocol**: Python's static type checker (pyright/mypy) catches this at type-check time. At runtime, `isinstance` check is available but not enforced in the constructor — matching the existing pattern where no runtime type validation is done on constructor args.
- **`scored_store` is provided AND `DATABASE_URL` is set**: No conflict — `ExerciseProgressStore` is simply not constructed. The env var is ignored.
- **`scored_store` is provided AND `DATABASE_URL` is NOT set**: Works correctly — `ExerciseProgressStore` is not constructed, so the missing env var doesn't cause an error.

## Rollout / rollback (if relevant)

- Rollout: Deploy updated `service.py`. All existing callers continue to work (they don't pass `scored_store`).
- Rollback: Revert `service.py`, `conftest.py`, and `test_sampling_weights.py` to previous versions.

## Notes / risks

- **Risk**: `@runtime_checkable` Protocol `isinstance` checks only verify method existence, not signatures.
  - **Mitigation**: This is documented Python behavior and is sufficient for our use case. Full signature checking is done by static type checkers (pyright/mypy), not runtime.
