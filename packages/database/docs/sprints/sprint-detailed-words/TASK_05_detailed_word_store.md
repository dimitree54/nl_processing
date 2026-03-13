---
Task ID: `T5`
Title: `Implement DetailedWordStore public API with unit tests`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `T4`
Parallelizable: `no`
---

## Goal / value

Implement the public `DetailedWordStore` class with `get_details()` and `get_or_extract_details()` methods. This is the main deliverable of the sprint's database side -- the typed persistence surface for rich lexical records. After this task, callers can persist and retrieve detailed-word records, with optional read-through extraction for cache misses.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-11 (DetailedWordStore API), FR-12 (schema_key, schema_version, payload), FR-13 (get_or_extract read-through), FR-14 (fail-fast for missing words, invalid payloads, unsupported versions), DEC-9 (inject extractor), DEC-10 (fail if source word missing), DEC-11 (same typed store for cache)
- Pattern reference: `src/nl_processing/database/service.py` (existing service pattern with injected backend)
- Pattern reference: `src/nl_processing/database/exercise_progress.py` (existing store with backend dependency)

## Preconditions

- T1 completed: `DetailedWordRecord`, `DetailedWordExtractorPort`, and detailed exceptions exist.
- T4 completed: Neon backend methods for get/upsert detailed words exist and are tested.

## Non-goals

- No E2E tests (that's T6).
- No modification to existing `service.py`, `exercise_progress.py`, or any existing public API.
- No real extractor implementation -- tests use fake/mock extractors.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/` -- new files: `detailed_word_store.py`, `_detailed_store_helpers.py`
- `tests/unit/database/` -- new files: `test_detailed_word_store.py`, `mock_detailed_backend.py`

**FORBIDDEN -- this task must NEVER touch:**
- `src/nl_processing/database/service.py` (existing)
- `src/nl_processing/database/exercise_progress.py` (existing)
- `tests/unit/database/mock_backend.py` (existing, 173 lines)
- `src/nl_processing/core/` or any core package file
- Any other module

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `make check` (in `packages/database/`)

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database/detailed_word_store.py` (~120-160 lines) -- Main `DetailedWordStore` class
- `src/nl_processing/database/_detailed_store_helpers.py` (~40-70 lines) -- Helper functions (row conversion, validation)
- `tests/unit/database/mock_detailed_backend.py` (~60-80 lines) -- In-memory mock for `AbstractDetailedWordBackend`
- `tests/unit/database/test_detailed_word_store.py` (~120-170 lines) -- Unit tests

## Dependencies and sequencing notes

- Depends on T1 for models, protocols, and exceptions.
- Depends on T4 for the Neon backend implementation (store must construct `NeonDetailedWordBackend` by default).
- T6 depends on this for E2E testing.
- T9 depends on this for the remote store interface used by cache.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `json` -- standard library, for `json.dumps()` / `json.loads()` of payloads.
- **Library**: `pydantic` -- already used. `DetailedWordRecord` model validation.
- No new dependencies.

## Implementation steps (developer-facing)

1. **Create `tests/unit/database/mock_detailed_backend.py`:**

   In-memory mock implementing the `AbstractDetailedWordBackend` contract:
   - `_details: dict[tuple[int, str], dict]` -- stores detail rows keyed by `(source_word_id, word_type)`
   - `get_word_details()`: return matching rows from in-memory store
   - `upsert_word_detail()`: store/overwrite in memory
   - `create_word_details_table()`: no-op

   Also needs a way to look up canonical words. The mock should integrate with the existing `MockBackend` or accept a word-lookup callable. Simplest approach: the mock takes a `word_lookup: dict[str, dict]` mapping `normalized_form -> word row dict`.

2. **Create `src/nl_processing/database/_detailed_store_helpers.py`:**

   Helper functions:
   - `row_to_detailed_record(row: dict) -> DetailedWordRecord`: Convert a backend row dict to the Pydantic model. Parse the `payload` field from JSON string to dict if needed.
   - `validate_payload(payload: dict) -> None`: Basic validation -- must be a non-empty dict. Raise `PayloadValidationError` if invalid.
   - `build_schema_key(source_lang: str, target_lang: str, word_type: str) -> str`: Construct the schema key string (e.g., `"nl_ru_noun"`).

3. **Create `src/nl_processing/database/detailed_word_store.py`:**

   ```python
   class DetailedWordStore:
       def __init__(
           self,
           source_language: Language,
           target_language: Language,
           backend: AbstractDetailedWordBackend | None = None,
           word_backend: AbstractBackend | None = None,
           extractor: DetailedWordExtractorPort | None = None,
       ) -> None:
           # If no backend provided, construct NeonDetailedWordBackend from DATABASE_URL
           # word_backend is needed to look up canonical source words (get_word)
           ...

       async def get_details(self, words: list[Word]) -> list[DetailedWordRecord]:
           """Return persisted detailed records for the given words.

           Raises SourceWordNotFoundError if any word is not in the canonical corpus.
           Returns only rows that exist; does NOT trigger extraction.
           """
           ...

       async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
           """Read persisted details first, extract only misses, persist results, return merged.

           Raises SourceWordNotFoundError if any word is not in the canonical corpus.
           Raises ValueError if no extractor is injected and there are misses.
           """
           ...
   ```

   Implementation logic for `get_details()`:
   1. For each word, look up canonical source word via `word_backend.get_word()`. Raise `SourceWordNotFoundError` if not found (FR-14, DEC-10).
   2. Collect source_word_ids.
   3. Call `backend.get_word_details()` with the IDs.
   4. Convert rows to `DetailedWordRecord` via helper.
   5. Return in input order (matching by source_word_id).

   Implementation logic for `get_or_extract_details()`:
   1. Call `get_details()` to get existing records.
   2. Identify misses (words without persisted details).
   3. If no misses, return existing records.
   4. If misses and no extractor: raise `ValueError("No extractor provided for missing details")`.
   5. Call `extractor.extract(missing_words)` to get new records.
   6. Validate each returned record's payload via `validate_payload()`.
   7. Persist each new record via `backend.upsert_word_detail()`.
   8. Return merged list in original input order.

4. **Create `tests/unit/database/test_detailed_word_store.py`:**

   Test cases:
   - **Constructor**: Store can be created with injected backends and extractor.
   - **`get_details()` happy path**: Word exists in corpus + detail exists -> returns `DetailedWordRecord`.
   - **`get_details()` missing corpus word**: Raises `SourceWordNotFoundError` (FR-14, FM-6).
   - **`get_details()` no persisted detail**: Returns empty list for that word (no error, just no data).
   - **`get_details()` preserves input order**: Multiple words return in order.
   - **`get_or_extract_details()` all cached**: Returns cached data, extractor NOT called.
   - **`get_or_extract_details()` some misses**: Extractor called with only misses, results persisted and merged.
   - **`get_or_extract_details()` no extractor + misses**: Raises `ValueError`.
   - **`get_or_extract_details()` missing corpus word**: Raises `SourceWordNotFoundError` before extraction.
   - **`get_or_extract_details()` invalid extractor payload**: Raises `PayloadValidationError`.
   - **Idempotent upsert**: Calling `get_or_extract_details()` twice returns same data, extractor called only once.

5. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: No database operations. Unit tests use mock backends only.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the `DatabaseService` and `ExerciseProgressStore` patterns for constructor, backend injection, and error handling.
- **Correct file locations**: New files in `src/nl_processing/database/` for source, `tests/unit/database/` for tests.
- **No regressions**: No existing files modified.

## Error handling + correctness rules (mandatory)

- `SourceWordNotFoundError` raised for missing canonical words (FR-14, FM-6).
- `PayloadValidationError` raised for invalid extractor output (FR-14).
- `ValueError` raised when extractor is needed but not injected.
- No empty catch blocks. No silent fallbacks.
- Extractor failures propagate to the caller (no catch-and-retry).

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database.detailed_word_store import DetailedWordStore` succeeds.
2. `DetailedWordStore(source_language=Language.NL, target_language=Language.RU, backend=mock, word_backend=mock)` creates a valid instance.
3. `get_details([word])` returns `DetailedWordRecord` for persisted data.
4. `get_details([unknown_word])` raises `SourceWordNotFoundError`.
5. `get_or_extract_details([word])` returns cached data without calling extractor.
6. `get_or_extract_details([new_word])` calls extractor, persists, and returns merged results.
7. `get_or_extract_details([new_word])` without extractor raises `ValueError`.
8. All unit tests pass.
9. `make check` passes in `packages/database/`.
10. All new files under 200 lines.

## Verification / quality gates

- [x] Unit tests added covering happy paths and error paths
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines
- [x] Negative-path tests for SourceWordNotFoundError, PayloadValidationError, missing extractor

## Edge cases

- Empty word list: `get_details([])` and `get_or_extract_details([])` should return `[]`.
- Word exists in corpus but has no detail yet: `get_details()` returns empty, `get_or_extract_details()` triggers extraction.
- Extractor returns records in different order than input: store must re-order to match input.
- Extractor returns fewer records than requested (e.g., skipped unsupported POS): store persists what's returned.
- `json.dumps()` / `json.loads()` for payload serialization: ensure dict round-trips correctly.

## Notes / risks

- **Risk**: The `DetailedWordStore` needs both `AbstractDetailedWordBackend` (for detail CRUD) and `AbstractBackend` (for `get_word()` canonical lookup).
  - **Mitigation**: The constructor accepts both as separate parameters. In production, both use the same database connection (Neon). In tests, both are mocked.
- **Design decision**: The store constructs `schema_key` as `"{src}_{tgt}_{word_type}"` (e.g., `"nl_ru_noun"`). This is a simple convention that the extractor can also follow.
- **Design decision**: `schema_version` starts at 1. The store does not enforce specific version values in V1 -- it stores whatever the extractor returns and includes the version in persisted rows. Full version compatibility checking is deferred until the extractor is implemented.
