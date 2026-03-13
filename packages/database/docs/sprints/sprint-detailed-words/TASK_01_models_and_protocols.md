---
Task ID: `T1`
Title: `Define DetailedWordRecord model, DetailedWordExtractorPort protocol, and new exceptions`
Sprint: `2026-03-13_detailed-words`
Module: `database`
Depends on: `--`
Parallelizable: `no`
---

## Goal / value

Establish the foundational data types, protocol interfaces, and exception classes that all subsequent tasks depend on. After this task, the `DetailedWordRecord` model, `DetailedWordExtractorPort` protocol, and detailed-word-specific exceptions exist and are importable.

## Context (contract mapping)

- Requirements: `packages/database/docs/module-spec.md` -- FR-11 (extractor protocol), FR-12 (schema_key, schema_version, payload), FR-14 (fail-fast exceptions), DEC-8, DEC-9, DEC-11
- Extractor module spec: `packages/extract_word_details/docs/module-spec.md` -- FR-1 (extract signature), FR-9 (versioned schema registry), IF-4
- Pattern reference: `packages/database_cache/src/nl_processing/database_cache/ports.py` -- existing `RemoteDeletePort` protocol pattern

## Preconditions

- None -- this is the first task.

## Non-goals

- No backend methods, SQL, or store implementation.
- No changes to existing `models.py`, `exceptions.py`, or any existing file.
- No test infrastructure beyond basic import/instantiation tests.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `src/nl_processing/database/` -- new files only
- `tests/unit/database/` -- new test files only

**FORBIDDEN -- this task must NEVER touch:**
- `src/nl_processing/database/models.py` (existing)
- `src/nl_processing/database/exceptions.py` (existing)
- `src/nl_processing/core/` or any core package file
- Any other module's code or tests

**Test scope:**
- Tests go in: `tests/unit/database/`
- Test command: `make check` (in `packages/database/`)
- NEVER run tests from other modules

## Touched surface (expected files / modules)

**New files to create:**
- `src/nl_processing/database/detailed_models.py` (~40-60 lines) -- `DetailedWordRecord` Pydantic model
- `src/nl_processing/database/detailed_ports.py` (~20-30 lines) -- `DetailedWordExtractorPort` protocol
- `src/nl_processing/database/detailed_exceptions.py` (~20-30 lines) -- Detailed-word-specific exceptions
- `tests/unit/database/test_detailed_models.py` (~40-60 lines) -- Model and protocol tests

## Dependencies and sequencing notes

- This is the foundation task. All other tasks depend on these types.
- No external dependencies beyond existing `pydantic`, `typing`, and `nl_processing.core.models`.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` -- already used in `database.models`. No new version needed.
- **Library**: `typing.Protocol` -- standard library, already used in `database_cache/ports.py`.
- No new third-party dependencies.

## Implementation steps (developer-facing)

1. **Create `src/nl_processing/database/detailed_models.py`:**
   - Define `DetailedWordRecord(BaseModel)` with fields:
     - `source_word: str` -- the canonical normalized_form of the source word
     - `word_type: str` -- the PartOfSpeech value string (e.g., "noun", "verb")
     - `schema_key: str` -- identifies the schema type (e.g., "nl_ru_noun")
     - `schema_version: int` -- integer version for compatibility checking
     - `payload: dict[str, Any]` -- the JSON-serializable detailed data
   - Import `Any` from `typing` and `BaseModel` from `pydantic`.

2. **Create `src/nl_processing/database/detailed_ports.py`:**
   - Define `DetailedWordExtractorPort(Protocol)` following the pattern from `database_cache/ports.py`:
     - Use `@runtime_checkable` decorator
     - Single method: `async def extract(self, words: list[Word]) -> list[DetailedWordRecord]`
   - Import `Word` from `nl_processing.core.models`.

3. **Create `src/nl_processing/database/detailed_exceptions.py`:**
   - `SourceWordNotFoundError(DatabaseError)` -- raised when a source word is not in the canonical corpus (FM-6)
   - `SchemaVersionError(DatabaseError)` -- raised when a persisted row has an unsupported schema version (FM-7)
   - `PayloadValidationError(DatabaseError)` -- raised when a payload fails validation (FR-14)
   - Import `DatabaseError` from `nl_processing.database.exceptions`.

4. **Create `tests/unit/database/test_detailed_models.py`:**
   - Test that `DetailedWordRecord` can be instantiated with valid data and serialized to dict.
   - Test that `DetailedWordRecord` rejects missing required fields (pydantic validation).
   - Test that `DetailedWordExtractorPort` is runtime-checkable (using `isinstance` with a conforming class).
   - Test that all three exception classes can be raised and caught as `DatabaseError`.
   - Test that exception messages propagate correctly.

5. **Run `make check`** in `packages/database/` and verify green.

## Production safety constraints (mandatory)

- **Database operations**: No database operations in this task. Only type definitions and unit tests.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse existing `DatabaseError` as base for new exceptions. Reuse `BaseModel` pattern from existing `models.py`. Reuse `Protocol` pattern from `database_cache/ports.py`.
- **Correct file locations**: New files in `src/nl_processing/database/` following existing naming conventions (`detailed_` prefix for new detailed-word files).
- **No regressions**: No existing files are modified, so no regressions possible.

## Error handling + correctness rules (mandatory)

- Exception classes must have clear, specific names and inherit from `DatabaseError`.
- No empty catch blocks. No blanket try/catch.

## Zero legacy tolerance rule (mandatory)

- N/A -- this task creates new code only.

## Acceptance criteria (testable)

1. `from nl_processing.database.detailed_models import DetailedWordRecord` succeeds.
2. `DetailedWordRecord(source_word="hond", word_type="noun", schema_key="nl_ru_noun", schema_version=1, payload={"article": "de"})` creates a valid instance.
3. `from nl_processing.database.detailed_ports import DetailedWordExtractorPort` succeeds and the protocol is `@runtime_checkable`.
4. `from nl_processing.database.detailed_exceptions import SourceWordNotFoundError, SchemaVersionError, PayloadValidationError` succeeds.
5. All three exceptions are subclasses of `DatabaseError`.
6. `make check` passes in `packages/database/`.

## Verification / quality gates

- [x] Unit tests added for models, protocol, and exceptions
- [x] Linters/formatters pass (`make check`)
- [x] No new warnings introduced
- [x] All new files under 200 lines (target <60 lines each)

## Edge cases

- `DetailedWordRecord` with empty `payload` dict should be valid (the store layer validates content, not the model).
- `schema_version` of 0 should be valid at the model level (version enforcement is at the store layer).

## Notes / risks

- **Risk**: The `DetailedWordRecord` model may evolve as the extractor is implemented.
  - **Mitigation**: Keep the model minimal and focused on what the database layer needs for persistence. The extractor will return this type.
- **Risk**: The `payload` field is `dict[str, Any]` which is very permissive.
  - **Mitigation**: This is intentional -- the database layer stores validated JSON. Validation logic lives in the store (T5), not the model.
