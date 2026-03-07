---
Task ID: `T3`
Title: `Update AbstractBackend with per-exercise-type and event-tracking methods`
Sprint: `2026-03-07_database-exercise-tables`
Module: `database`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Update `AbstractBackend` to reflect the new per-exercise-type table structure. The `increment_user_exercise_score` and `get_user_exercise_scores` methods change signatures (table param now includes exercise slug, `exercise_type` param removed). Add new abstract methods for event tracking (`check_event_applied`, `mark_event_applied`). Update `create_tables` signature to accept `exercise_slugs`.

## Context (contract mapping)

- Requirements: Sprint request items 1 (per-exercise tables), 2 (constructor change), 3 (cache support APIs)
- Current: `abstract.py` (95 lines) has `increment_user_exercise_score(table, user_id, source_word_id, exercise_type, delta)` and `get_user_exercise_scores(table, user_id, source_word_ids, exercise_types)`.
- New: `exercise_type` is implicit in the table name. Methods lose the `exercise_type`/`exercise_types` params. `create_tables` gains `exercise_slugs` param.

## Preconditions

- T2 completed (query templates updated).

## Non-goals

- Implementing the concrete backend (T4).
- Touching `_queries.py` (done in T2).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/database/backend/abstract.py` — abstract method signatures

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/database/backend/_queries.py` (already done in T2)
- `nl_processing/database/backend/neon.py` (done in T4)
- Any test files
- Any other module

**Test scope:**
- No tests for this task (ABC changes are verified when concrete implementations are tested in T4/T9/T10).
- Linter check: `uv run ruff check nl_processing/database/backend/abstract.py`

## Touched surface (expected files / modules)

- `nl_processing/database/backend/abstract.py`

## Dependencies and sequencing notes

- Depends on T2 (queries must be in place to understand the new parameter shapes).
- T4 depends on this (NeonBackend implements these abstract methods).

## Implementation steps (developer-facing)

1. **Update `increment_user_exercise_score`**:
   - Remove `exercise_type: str` parameter.
   - New signature: `async def increment_user_exercise_score(self, table: str, user_id: str, source_word_id: int, delta: int) -> int`
   - Update docstring: "table includes exercise slug suffix (e.g., `nl_ru_flashcard`)."

2. **Update `get_user_exercise_scores`**:
   - Remove `exercise_types: list[str]` parameter.
   - Remove `source_word_ids` (query is per-table now, so caller iterates tables).
   - New signature: `async def get_user_exercise_scores(self, table: str, user_id: str, source_word_ids: list[int]) -> list[dict[str, str | int]]`
   - Return dicts now have `source_word_id` and `score` (no `exercise_type`).

3. **Update `create_tables`**:
   - Add `exercise_slugs: list[str]` parameter.
   - New signature: `async def create_tables(self, languages: list[str], pairs: list[tuple[str, str]], exercise_slugs: list[str]) -> None`
   - Update docstring: "Creates per-exercise-type score tables for each (pair, exercise_slug) combination."

4. **Add `check_event_applied`**:
   ```python
   @abstractmethod
   async def check_event_applied(self, table: str, event_id: str) -> bool:
       """Return True if event_id has already been applied."""
   ```

5. **Add `mark_event_applied`**:
   ```python
   @abstractmethod
   async def mark_event_applied(self, table: str, event_id: str) -> None:
       """Record event_id as applied. Idempotent (ON CONFLICT DO NOTHING)."""
   ```

6. **Line count check**: Current is 95 lines. Adding ~20 lines for new methods + docstrings. Estimate ~115 lines. Well under 200.

7. **Linter check**:
   ```
   uv run ruff format nl_processing/database/backend/abstract.py
   uv run ruff check nl_processing/database/backend/abstract.py
   ```

## Production safety constraints (mandatory)

- **Database operations**: ABC — no actual DB operations. Pure interface definition.
- **Resource isolation**: N/A.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extends existing ABC pattern.
- **No regressions**: Changing abstract method signatures will cause `NeonBackend` to fail type checks until T4 updates it. This is expected.

## Error handling + correctness rules (mandatory)

- Abstract methods have no implementation. Error handling is in concrete implementations.

## Zero legacy tolerance rule (mandatory)

- Old method signatures (`exercise_type` param, `exercise_types` param, 2-param `create_tables`) are fully replaced — no backwards-compatible wrappers.

## Acceptance criteria (testable)

1. `increment_user_exercise_score` has 4 params: `table`, `user_id`, `source_word_id`, `delta` (no `exercise_type`).
2. `get_user_exercise_scores` has 3 params: `table`, `user_id`, `source_word_ids` (no `exercise_types`).
3. `create_tables` has 3 params: `languages`, `pairs`, `exercise_slugs`.
4. `check_event_applied(table, event_id) -> bool` exists as abstract method.
5. `mark_event_applied(table, event_id) -> None` exists as abstract method.
6. `uv run ruff check nl_processing/database/backend/abstract.py` — no errors.
7. File is ≤ 200 lines.

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] File ≤ 200 lines

## Edge cases

- None for abstract methods.

## Notes / risks

- **Risk**: After this task and before T4, `NeonBackend` will not satisfy the ABC. This is expected — T3 and T4 are sequential. Do not attempt to run tests between T3 and T4.
