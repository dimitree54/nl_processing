---
Task ID: `T2`
Title: `Enrich export_remote_snapshot() with added_at and create local enriched snapshot type (FR-10)`
Sprint: `2026-03-12_personal-vocab`
Module: `database`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

`export_remote_snapshot()` must include `added_at` alongside stable IDs and score maps so `database_cache` can rebuild the personal-vocabulary read model locally (FR-10, CR-3). Since `WordPairSnapshot` lives in `core` and cannot be modified, this task creates a local enriched snapshot type in `database.models` and updates `ExerciseProgressStore.export_remote_snapshot()` to return it.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-10 (cache-facing snapshot includes added_at), CR-3 (reads and snapshots share ordering and field set), BR-6 (added_at from user_words.added_at)
- Module spec: `docs/module-spec.md`
- Core models: `packages/core/src/nl_processing/core/models.py` — `WordPairSnapshot(ScoredWordPair)` with `target_word_id: int` (read-only, not modified)

## Preconditions

- T1 is complete: `get_user_words` backend query now returns `added_at` in the row dict.
- `MockBackend._build_joined_row()` includes `"added_at"` key.

## Non-goals

- Modifying `core` package models.
- Implementing `list_personal_words()` (that is T3).
- Implementing `get_progress_summary()` (that is T4).
- Adding delete functionality (that is T5).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database/models.py` — add `EnrichedWordPairSnapshot` model
- `src/nl_processing/database/exercise_progress.py` — update `export_remote_snapshot()` return type and implementation; extract helpers if approaching 200 lines
- `tests/unit/database/test_exercise_progress.py` — update/add snapshot tests
- `tests/integration/database/` — add integration test for enriched snapshot if appropriate

**FORBIDDEN — this task must NEVER touch:**
- `packages/core/src/nl_processing/core/models.py` or any `core` package file
- Any other module's code or tests
- Bot code

**Test scope:**
- Tests go in: `tests/unit/database/`, `tests/integration/database/`
- Test command: `make check`
- NEVER run the full monorepo test suite

## Touched surface (expected files / modules)

- `src/nl_processing/database/models.py` — new `EnrichedWordPairSnapshot` model
- `src/nl_processing/database/exercise_progress.py` — update `export_remote_snapshot()` to read `added_at` from rows and return `EnrichedWordPairSnapshot` list; potentially extract `_row_to_word_pair` and `_word_from_row` helpers into a shared location if file size requires
- `tests/unit/database/test_exercise_progress.py` — update `test_export_remote_snapshot` to assert `added_at` field is present and is a `datetime`; update type assertions to `EnrichedWordPairSnapshot`

## Dependencies and sequencing notes

- Depends on T1 because the `added_at` field must be present in backend row dicts.
- T3 and T4 depend on this task because they need the enriched row parsing and the `_get_rows_with_scores()` helper to return `added_at`.

## Third-party / library research (mandatory for any external dependency)

No new external dependencies. Uses:
- `datetime` from stdlib (already used in mock)
- `pydantic.BaseModel` (already a project dependency for models)
- `WordPairSnapshot` from `nl_processing.core.models` (read-only, for inheritance)

## Implementation steps (developer-facing)

1. **Create `EnrichedWordPairSnapshot` in `models.py`**:
   - Add `from datetime import datetime` import.
   - Add `from nl_processing.core.models import WordPairSnapshot` import (if not already present; currently the file only imports `Word`).
   - Define:
     ```python
     class EnrichedWordPairSnapshot(WordPairSnapshot):
         """Snapshot with added_at for cache-side personal-vocabulary reads (FR-10, CR-3)."""
         added_at: datetime
     ```
   - This extends `WordPairSnapshot` (which has `pair`, `scores`, `source_word_id`, `target_word_id`) with `added_at`.
   - `models.py` goes from 7 lines to ~18 lines — well under 200.

2. **Update `export_remote_snapshot()` in `exercise_progress.py`**:
   - Import `EnrichedWordPairSnapshot` from `nl_processing.database.models`.
   - Import `datetime` from stdlib (if not already present).
   - Change return type annotation from `list[WordPairSnapshot]` to `list[EnrichedWordPairSnapshot]`.
   - In the loop, read `added_at` from each row: `added_at = row["added_at"]` (it's a `datetime` from asyncpg or mock).
   - Replace `WordPairSnapshot(...)` construction with `EnrichedWordPairSnapshot(pair=..., scores=..., source_word_id=..., target_word_id=..., added_at=added_at)`.
   - **Line count check**: `exercise_progress.py` is at 195. The import adds ~1 line, the `added_at` extraction ~1 line, the constructor change ~1 line (net). This puts it at ~198. If it goes over 200, extract `_word_from_row` and `_row_to_word_pair` methods into a new `src/nl_processing/database/_row_helpers.py` file and import them. Both methods are pure functions that take a row dict and return a model — natural extraction candidates.

3. **Update the `_get_rows_with_scores()` return type** (if needed):
   - The current return is `tuple[list[dict[str, str | int]], dict[int, dict[str, int]]]`. The row dicts now include `"added_at"` (a `datetime`), so the type hint `dict[str, str | int]` is slightly inaccurate but `asyncpg` rows always return mixed types. Consider updating to `dict[str, object]` or `dict[str, str | int | datetime]` for accuracy. The developer should pick the pragmatic option that keeps things clean.

4. **Update unit test `test_export_remote_snapshot`**:
   - Update the import to use `EnrichedWordPairSnapshot` instead of (or in addition to) `WordPairSnapshot`.
   - Assert `isinstance(snapshot[0], EnrichedWordPairSnapshot)`.
   - Assert `snapshot[0].added_at` is a `datetime` instance.
   - Since `EnrichedWordPairSnapshot` extends `WordPairSnapshot`, `isinstance(snapshot[0], WordPairSnapshot)` still holds true — which is good for backward compatibility with any code that type-checks against `WordPairSnapshot`.

5. **Run `make check`** and verify all tests pass.

## Production safety constraints (mandatory)

- **Database operations**: No writes, no DDL. Only the SELECT output is consumed differently.
- **Resource isolation**: No new resource usage. Tests use existing Doppler-managed `DATABASE_URL`.
- **Migration preparation**: N/A — no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends `WordPairSnapshot` via inheritance — no duplication of fields.
- **Correct libraries only**: `pydantic`, `datetime` — already used.
- **Correct file locations**: Model in `models.py`, logic in `exercise_progress.py`.
- **No regressions**: `EnrichedWordPairSnapshot` is a subclass of `WordPairSnapshot`, so any code expecting `WordPairSnapshot` instances still works via Liskov substitution. Existing tests that check `isinstance(..., WordPairSnapshot)` still pass.

## Error handling + correctness rules (mandatory)

- `added_at` is `NOT NULL` in the DB — no `None` handling needed.
- No new error paths. The field is always present in rows from T1.
- No empty `catch` blocks or silenced errors.

## Zero legacy tolerance rule (mandatory)

- The old `WordPairSnapshot` import in `exercise_progress.py` is replaced by `EnrichedWordPairSnapshot` for the `export_remote_snapshot()` method. If `WordPairSnapshot` is still needed by other methods (e.g., `get_word_pairs_with_scores` returns `ScoredWordPair`, not `WordPairSnapshot`), the import is only removed from the snapshot method's usage, not from the file entirely.
- Remove any dead imports after the change.

## Acceptance criteria (testable)

1. `EnrichedWordPairSnapshot` exists in `database.models` with fields: `pair`, `scores`, `source_word_id`, `target_word_id` (inherited from `WordPairSnapshot`), plus `added_at: datetime`.
2. `export_remote_snapshot()` return type is `list[EnrichedWordPairSnapshot]`.
3. Each returned snapshot has an `added_at` field that is a `datetime` instance.
4. `isinstance(snapshot, WordPairSnapshot)` is `True` for any `EnrichedWordPairSnapshot` — backward compatible.
5. Unit test asserts `added_at` presence and type.
6. `exercise_progress.py` stays at or under 200 lines (decompose if needed).
7. `make check` is green.

## Verification / quality gates

- [ ] Unit tests pass, including updated snapshot test asserting `added_at`
- [ ] Integration tests pass
- [ ] E2e tests pass (existing `test_export_remote_snapshot` equivalent, if any)
- [ ] `make check` green
- [ ] No new warnings introduced
- [ ] `exercise_progress.py` ≤ 200 lines (verified via `wc -l` or pylint)

## Edge cases

- `added_at` is always present (NOT NULL) — no None handling needed.
- `EnrichedWordPairSnapshot` is a subclass of `WordPairSnapshot` — existing code consuming `WordPairSnapshot` is not broken.
- If `exercise_progress.py` hits exactly 200 lines: extract `_word_from_row` + `_row_to_word_pair` into `_row_helpers.py`.

## Notes / risks

- **Risk**: `exercise_progress.py` (195 lines) may exceed 200 after changes.
  - **Mitigation**: If the file reaches 197+, extract the two pure-function helpers (`_word_from_row`, `_row_to_word_pair`) into `src/nl_processing/database/_row_helpers.py`. Both are stateless and depend only on `core.models`.
- **Risk**: Callers of `export_remote_snapshot()` outside this module may expect `WordPairSnapshot` return type.
  - **Mitigation**: `EnrichedWordPairSnapshot` IS-A `WordPairSnapshot` (inheritance). No downstream breakage.
- **Cross-package note**: If the `core` team later adds `added_at` to `WordPairSnapshot`, the local `EnrichedWordPairSnapshot` can be collapsed back. Flag this for future cleanup.
