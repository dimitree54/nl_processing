---
Sprint ID: `2026-03-08_sampling-swappable-store`
Sprint Goal: Add Protocol-based data source injection to `WordSampler` so it works with either remote DB or local cache
Sprint Type: module
Module: `sampling`
Status: planning
---

## Goal

Add a `ScoredPairProvider` Protocol to the `sampling` module and modify `WordSampler` to accept an optional `scored_store` parameter. This enables the sampler to use either `ExerciseProgressStore` (remote Neon) or `DatabaseCacheService` (local SQLite cache) as its data source without coupling to either. Update tests to verify both construction paths and structural typing conformance. Update the vulture whitelist for the new Protocol symbol.

## Module Scope

### What this sprint implements
- Module: `sampling` (weighted random sampling of practice items)
- Architecture spec: `nl_processing/sampling/docs/architecture_sampling.md` (section "Protocol-Based Data Source Injection")
- PRD: `nl_processing/sampling/docs/prd_sampling.md` (FR21–FR25)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/sampling/service.py` — add `ScoredPairProvider` Protocol, modify `WordSampler.__init__`
- `tests/unit/sampling/conftest.py` — update `sampler` fixture, add injection-path fixture
- `tests/unit/sampling/test_sampling_weights.py` — add Protocol conformance / injection-path tests
- `vulture_whitelist.py` — add `ScoredPairProvider` entry

**FORBIDDEN — this sprint must NEVER touch:**
- `nl_processing/database/` — no changes to `ExerciseProgressStore`
- `nl_processing/database_cache/` — no changes to `DatabaseCacheService`
- `nl_processing/core/` — no changes
- Any other module's code or tests
- Bot code
- `nl_processing/sampling/docs/` — docs already updated
- `pyproject.toml`, `ruff.toml`, `Makefile`, `.jscpd.json`

### Test Scope
- **Test directory**: `tests/unit/sampling/`
- **Test command**: `uv run pytest tests/unit/sampling/ -x -v`
- **Full quality gate**: `make check`
- **NEVER run**: `uv run pytest` (full suite) outside of `make check`

## Interface Contract

### Public interface this sprint modifies

```python
from typing import Protocol
from nl_processing.database.models import ScoredWordPair


class ScoredPairProvider(Protocol):
    """Any object that can return scored word pairs."""

    async def get_word_pairs_with_scores(self) -> list[ScoredWordPair]: ...


class WordSampler:
    def __init__(
        self,
        *,
        user_id: str,
        source_language: Language = Language.NL,
        target_language: Language = Language.RU,
        exercise_types: list[str],
        positive_balance_weight: float = 0.01,
        scored_store: ScoredPairProvider | None = None,  # NEW
    ) -> None: ...
```

When `scored_store` is provided, it is used as `self._progress_store` directly. When `None`, `ExerciseProgressStore` is constructed as before (backward compatibility per FR24).

## Scope

### In
- Add `ScoredPairProvider` Protocol to `nl_processing/sampling/service.py`
- Modify `WordSampler.__init__` to accept optional `scored_store` parameter
- Update `self._progress_store` type annotation to `ScoredPairProvider`
- Update test conftest to verify injection path
- Add structural typing conformance tests for `MockProgressStore` and `DatabaseCacheService`
- Update vulture whitelist for `ScoredPairProvider`

### Out
- No changes to `ExerciseProgressStore` or `DatabaseCacheService` (FR23 — they already conform structurally)
- No integration or E2E tests (pure refactor, no new external behavior)
- No docs changes (already done)
- No new sampling logic or policy changes

## Inputs (contracts)

- Requirements: `nl_processing/sampling/docs/prd_sampling.md` (FR21–FR25)
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md` ("Protocol-Based Data Source Injection")
- Existing code: `nl_processing/sampling/service.py`, `tests/unit/sampling/conftest.py`
- Provider implementations: `nl_processing/database/exercise_progress.py`, `nl_processing/database_cache/service.py`
- Vulture whitelist: `vulture_whitelist.py`

## Change digest

- **Requirement deltas**: FR21–FR25 are new requirements added to the PRD. They describe Protocol-based data source injection for `WordSampler`.
- **Architecture deltas**: "Protocol-Based Data Source Injection" section added to architecture doc. Both documents are already finalized — no changes needed this sprint.

## Task list (dependency-aware)

- **T1:** `TASK_01_protocol_and_constructor.md` (depends: —) (parallel: no) — Add `ScoredPairProvider` Protocol, modify `WordSampler.__init__`, update tests for both paths + structural typing conformance
- **T2:** `TASK_02_vulture_whitelist.md` (depends: T1) (parallel: no) — Add `ScoredPairProvider` to vulture whitelist, run `make check`

## Dependency graph (DAG)

```
T1 → T2
```

## Execution plan

### Critical path
T1 → T2

### Parallel tracks (lanes)
- **Lane A (only lane)**: T1, T2 — sequential; T2 depends on T1 (Protocol must exist before whitelisting)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All tests use mocked stores (no DB connections). The `sampler` fixture uses a dummy `DATABASE_URL` env var — never a real connection.
- **Shared resource isolation**: N/A — no files, ports, sockets, or databases are used. All tests run in-memory with mock stores.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- [ ] All tasks completed and verified
- [ ] Unit tests pass: `uv run pytest tests/unit/sampling/ -x -v`
- [ ] Module isolation: no files outside the ALLOWED list were touched
- [ ] Public interface matches architecture spec exactly (Protocol + constructor signature)
- [ ] Backward compatibility: existing constructor usage (without `scored_store`) continues to work
- [ ] Zero legacy tolerance: `patch_store` helper removed or updated; no dead code
- [ ] No errors are silenced (no swallowed exceptions)
- [ ] Requirements/architecture docs unchanged
- [ ] Production database untouched
- [ ] `make check` passes (ruff, pylint 200-line, vulture, jscpd, all test suites)
- [ ] All source files ≤ 200 lines

## Risks + mitigations

- **Risk**: `typing.Protocol` with async methods — runtime `isinstance` checks don't validate method signatures without `runtime_checkable`.
  - **Mitigation**: T1 includes adding `@runtime_checkable` decorator and an explicit `isinstance` assertion test.
- **Risk**: Existing tests break if `conftest.py` changes affect the `sampler` fixture.
  - **Mitigation**: T1 preserves the existing `sampler` fixture behavior (backward-compat path with monkeypatched `DATABASE_URL`). New injection-path tests are added alongside, not replacing.
- **Risk**: `service.py` exceeds 200-line limit after adding Protocol.
  - **Mitigation**: Current file is 105 lines. Protocol adds ~8 lines, constructor change adds ~5 lines. Total ~118 lines — well under 200.

## Rollback / recovery notes

- Revert the 4 files touched: `service.py`, `conftest.py`, `test_sampling_weights.py`, `vulture_whitelist.py`.
- No data model changes, no migrations, no external state to clean up.

## Task validation status

- Per-task validation order: T1 → T2
- Validator: self-validated against checklists + task-checker
- Outcome: pending
- Notes: —

## Sources used

- Requirements: `nl_processing/sampling/docs/prd_sampling.md`
- Architecture: `nl_processing/sampling/docs/architecture_sampling.md`
- Code read: `nl_processing/sampling/service.py`, `nl_processing/database/exercise_progress.py`, `nl_processing/database_cache/service.py`, `nl_processing/database/models.py`
- Tests read: `tests/unit/sampling/conftest.py`, `tests/unit/sampling/test_sampling_weights.py`, `tests/unit/sampling/test_sampling_adversarial.py`
- Build config: `Makefile`, `pyproject.toml`, `vulture_whitelist.py`
- Sprint patterns: `docs/sprints/database-cache-impl/` (for whitelist task pattern)

## Contract summary

### What (requirements)
- FR21: `WordSampler` accepts optional `scored_store` parameter
- FR22: `scored_store` conforms to `ScoredPairProvider` Protocol with `get_word_pairs_with_scores()`
- FR23: Both `ExerciseProgressStore` and `DatabaseCacheService` satisfy `ScoredPairProvider` structurally
- FR24: Without `scored_store`, sampler falls back to constructing `ExerciseProgressStore`
- FR25: Sampler must not import `DatabaseCacheService`

### How (architecture)
- `ScoredPairProvider` is a `typing.Protocol` in `sampling/service.py`
- `WordSampler.__init__` gets optional `scored_store: ScoredPairProvider | None = None`
- When provided, `self._progress_store` is set to the injected store
- When not provided, `ExerciseProgressStore` is constructed as before

## Impact inventory (implementation-facing)

- **Module**: `sampling` (`nl_processing/sampling/`)
- **Interfaces**: `ScoredPairProvider` (new Protocol), `WordSampler.__init__` (modified signature)
- **Data model**: No changes
- **External services**: None — sampler reads from injected store (mocked in tests)
- **Test directory**: `tests/unit/sampling/`
