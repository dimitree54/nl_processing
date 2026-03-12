---
Task ID: `T3`
Title: `Implement list_personal_words() on DatabaseService (FR-7)`
Sprint: `2026-03-12_personal-vocab`
Module: `database`
Depends on: `T2`
Parallelizable: `yes, with T4 and T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Expose `list_personal_words()` on `DatabaseService` that returns the full translated personal vocabulary for a user — including stable source and target IDs, `user_words.added_at`, and per-exercise scores. This is the ergonomic "whole personal database" read surface requested in FR-7.

## Context (contract mapping)

- Requirements: `docs/module-spec.md` — FR-7 (personal-vocabulary read API with stable IDs, added_at, per-exercise scores), BR-6 (added_at from user_words.added_at), CR-3 (reads and snapshots share ordering and field set)
- Module spec: `docs/module-spec.md` — IF-1 (DatabaseService.list_personal_words()), Processing Flow step 4

## Preconditions

- T1 complete: `get_user_words` backend query returns `added_at`.
- T2 complete: `EnrichedWordPairSnapshot` model exists in `database.models`; `_get_rows_with_scores()` helper works with `added_at` in rows.

## Non-goals

- Implementing `get_progress_summary()` (T4).
- Implementing delete APIs (T5).
- Filtering personal words by word_type or other criteria (FR-7 returns all translated entries).
- Pagination (not specified in requirements).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `src/nl_processing/database/service.py` — add `list_personal_words()` method
- `src/nl_processing/database/models.py` — add `PersonalWord` model
- `src/nl_processing/database/exercise_progress.py` — potentially reuse or adapt `_get_rows_with_scores()` helper
- `tests/unit/database/test_service.py` — add unit tests for `list_personal_words()`
- `tests/unit/database/conftest.py` — add `exercise_types` fixture support for `DatabaseService` if needed
- `tests/integration/database/` — add integration test for `list_personal_words()`
- `tests/e2e/database/` — add e2e test for `list_personal_words()`

**FORBIDDEN — this task must NEVER touch:**
- `packages/core/` or any core package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database/`, `tests/integration/database/`, `tests/e2e/database/`
- Test command: `make check`

## Touched surface (expected files / modules)

- `src/nl_processing/database/models.py` — `PersonalWord` model
- `src/nl_processing/database/service.py` — `list_personal_words()` method
- `tests/unit/database/test_service.py` — unit tests
- `tests/unit/database/conftest.py` — possible fixture update
- `tests/integration/database/` — integration test
- `tests/e2e/database/` — e2e test

## Dependencies and sequencing notes

- Depends on T2 because it needs `added_at` in row dicts and the enriched model pattern.
- Parallel with T4 and T5 — no file contention. T3 primarily touches `service.py` and `test_service.py`; T4 touches `exercise_progress.py` and `test_exercise_progress.py`; T5 touches new backend files.

## Third-party / library research (mandatory for any external dependency)

No new external dependencies. Uses:
- `pydantic.BaseModel` — for `PersonalWord`
- `datetime` — for `added_at` field type
- Existing backend methods and `ExerciseProgressStore` patterns

## Implementation steps (developer-facing)

1. **Create `PersonalWord` model in `models.py`**:
   ```python
   from datetime import datetime
   from nl_processing.core.models import Word, WordPair, WordPairSnapshot

   class PersonalWord(BaseModel):
       """Full personal-vocabulary entry with stable IDs, added_at, and scores (FR-7)."""
       pair: WordPair
       source_word_id: int
       target_word_id: int
       added_at: datetime
       scores: dict[str, int]
   ```
   - `models.py` should stay well under 200 lines after this addition.

2. **Add `list_personal_words()` to `DatabaseService`**:
   - `DatabaseService` needs access to exercise score data. The method needs to know which `exercise_types` to query scores for.
   - **Design decision (decided)**: `list_personal_words()` accepts `exercise_types: list[str]` as a method parameter. Rationale: `DatabaseService` does not currently store exercise types, and not all callers need exercise-aware reads. Adding it to `__init__` would change the constructor contract for all callers.
   - Implementation:
     - Fetch rows via `self._backend.get_user_words(self._user_id, self._source_language.value)` — returns rows with `added_at`.
     - Fetch scores for each exercise type via `self._backend.get_user_exercise_scores()` — same pattern as `ExerciseProgressStore._get_rows_with_scores()`.
     - Build `PersonalWord` instances from the combined data.
   - **Line count**: `service.py` is at 180 lines. Adding `list_personal_words()` (~25-30 lines) pushes it to ~210. **Decompose by extracting `_translate_and_store()` and its helper into a new `src/nl_processing/database/_translation.py`** private module. This removes ~25 lines from `service.py`, making room for the new method. `_translate_and_store` is a self-contained fire-and-forget background task — a natural extraction candidate.

3. **Handle the score-fetching pattern**:
   - The score tables are named `{src}_{tgt}_{exercise_type}` (e.g., `nl_ru_flashcard`).
   - `list_personal_words()` needs the source and target language values to build score table names.
   - Fetch source_word_ids from the rows, then for each exercise type, call `self._backend.get_user_exercise_scores(score_table, self._user_id, source_word_ids)`.
   - Build a `scores_by_word: dict[int, dict[str, int]]` mapping, defaulting missing scores to `0`.

4. **Construct `PersonalWord` objects**:
   - For each row:
     ```python
     PersonalWord(
         pair=WordPair(source=..., target=...),
         source_word_id=int(row["source_id"]),
         target_word_id=int(row["target_id"]),
         added_at=row["added_at"],
         scores={et: scores_by_word.get(wid, {}).get(et, 0) for et in exercise_types},
     )
     ```

5. **Write unit tests in `test_service.py`**:
   - `test_list_personal_words_returns_entries`: Seed a word pair with translation link via mock backend, call `list_personal_words(exercise_types=["flashcard"])`, assert returns `PersonalWord` with correct fields.
   - `test_list_personal_words_includes_added_at`: Assert `added_at` is a `datetime`.
   - `test_list_personal_words_includes_scores`: Seed score data in mock backend, assert scores are populated.
   - `test_list_personal_words_missing_scores_default_zero`: No scores seeded → assert `scores["flashcard"] == 0`.
   - `test_list_personal_words_empty`: No words → returns empty list.
   - `test_list_personal_words_excludes_untranslated`: Words without translations are not included (INNER JOIN behavior).
   - **Line count for `test_service.py`**: Currently 182 lines. Adding ~40 lines of tests → ~222 lines. **Must decompose**: create `tests/unit/database/test_personal_vocab.py` for the new tests, or split the existing file.

6. **Write integration test** (in a new `tests/integration/database/test_personal_vocab.py` or in the existing test file):
   - Insert words, translations, user associations, and exercise scores.
   - Call `list_personal_words()` via a `DatabaseService` instance with a real Neon backend.
   - Assert `PersonalWord` fields: `source_word_id`, `target_word_id`, `added_at` (datetime), `scores` populated.

7. **Write e2e test** (in a new `tests/e2e/database/test_personal_vocab.py`):
   - Full flow: add words via service (with translator), wait for translations, call `list_personal_words()`.
   - Assert all added words appear with `added_at` and default scores.

8. **Run `make check`** and verify all tests pass, all files under 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: Read-only queries against test DB. No writes beyond test data setup.
- **Resource isolation**: UUID-based user isolation. No port/file conflicts.
- **Migration preparation**: N/A — no schema changes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse the existing `get_user_words` backend method and score-fetching pattern from `ExerciseProgressStore`.
- **Correct libraries only**: `pydantic`, `datetime` — already used.
- **Correct file locations**: Follow existing patterns — model in `models.py`, service method on `DatabaseService`.
- **No regressions**: New method; no changes to existing methods.
- **File decomposition**: `service.py` (180 lines) and `test_service.py` (182 lines) will both need decomposition when adding this feature. Plan the split as part of this task, not as a separate task.

## Error handling + correctness rules (mandatory)

- If `exercise_types` is empty or not provided, the method should still return `PersonalWord` entries with empty `scores` dicts. No exception needed for empty exercise_types in this context (unlike `ExerciseProgressStore.__init__` which requires non-empty).
- No silenced errors. Backend failures propagate naturally.

## Zero legacy tolerance rule (mandatory)

- No dead code introduced. If `_get_rows_with_scores()` logic is extracted into a shared helper, remove the duplicate from its original location.
- If `_translate_and_store` is extracted from `service.py` to make room, update all references.

## Acceptance criteria (testable)

1. `PersonalWord` model exists in `database.models` with fields: `pair: WordPair`, `source_word_id: int`, `target_word_id: int`, `added_at: datetime`, `scores: dict[str, int]`.
2. `DatabaseService.list_personal_words(exercise_types=...)` returns `list[PersonalWord]`.
3. Each `PersonalWord` has stable `source_word_id` and `target_word_id` matching the DB rows.
4. `added_at` is a `datetime` sourced from `user_words.added_at` (BR-6).
5. `scores` contains per-exercise-type scores, defaulting missing scores to `0`.
6. Untranslated words are excluded (INNER JOIN behavior maintained).
7. Unit tests cover: normal flow, empty list, scores present, scores default to 0, untranslated exclusion.
8. Integration test confirms real DB returns correct `PersonalWord` structure.
9. E2e test confirms full add-translate-read flow.
10. `service.py` ≤ 200 lines (decomposition done if needed).
11. `test_service.py` ≤ 200 lines (decomposition done if needed).
12. `make check` is green.

## Verification / quality gates

- [ ] Unit tests added for `list_personal_words()` (happy path, empty, scores, no scores, untranslated)
- [ ] Integration test added
- [ ] E2e test added
- [ ] `make check` green
- [ ] No new warnings
- [ ] All source files ≤ 200 lines
- [ ] All test files ≤ 200 lines

## Edge cases

- No words in user's vocabulary → returns empty list.
- Words exist but no translations → excluded (INNER JOIN).
- No scores for any exercise type → `scores` dict has all values as `0`.
- Multiple exercise types → all appear in `scores` dict.
- `exercise_types=[]` → `scores` is empty dict `{}` for each word.

## Notes / risks

- **Risk**: `service.py` (180 lines) will exceed 200 when adding `list_personal_words()`.
  - **Mitigation**: Extract `_translate_and_store()` into `src/nl_processing/database/_translation.py` to free ~25 lines.
- **Risk**: `test_service.py` (182 lines) will exceed 200 when adding new tests.
  - **Mitigation**: Create `tests/unit/database/test_personal_vocab.py` for the new tests.
- **Risk**: Score-fetching logic duplicated between `ExerciseProgressStore._get_rows_with_scores()` and the new `list_personal_words()`.
  - **Mitigation**: Extract the shared "fetch rows + fetch scores per exercise type" pattern into a standalone async helper in `src/nl_processing/database/_score_helpers.py`. Both `ExerciseProgressStore` and `DatabaseService.list_personal_words()` call this helper. Remove the duplicate from its original location.
- **CR-3 note**: The ordering and field set of `list_personal_words()` must match `export_remote_snapshot()`. Both use the same `get_user_words` backend query and should iterate rows in the same order.
