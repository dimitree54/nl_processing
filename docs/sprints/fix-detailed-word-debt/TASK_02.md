---
Task ID: T2
Title: Add `PayloadValidatorPort` and wire validation into `DetailedWordStore`
Sprint: `2026-03-13_fix-detailed-word-debt`
Module: database
Depends on: T1
Parallelizable: yes, with T3
---

## Goal / value

After this task, `DetailedWordStore` validates payloads on both read and write paths through an injected `PayloadValidatorPort`. `SchemaVersionError` and `PayloadValidationError` (already defined in `detailed_exceptions.py`) are actually raised by the store when validation fails. This fulfills FR-14, BR-9, NFR-4, CR-4, and FM-7 from the database module spec. Validation is optional (backwards-compatible) -- when no validator is injected, the store behaves exactly as before.

## Context (contract mapping)

- FR-14 in `packages/database/docs/module-spec.md`: "The store must reject missing canonical source words, unsupported schema versions, and invalid payloads instead of silently creating fallback rows."
- BR-9: "Detailed-word rows must store only schema-validated payloads and must be parseable through the extractor-owned registry."
- NFR-4: "Detailed-word payloads must never bypass typed validation. Validate before write and after read."
- CR-4: "`DetailedWordStore` must round-trip payloads through the same schema registry and version parser defined by `extract_word_details`."
- FM-7: "Persisted detailed payload does not match the declared schema version or schema key -> Raise an explicit database-layer error and reject the row."

**Circular dependency avoidance**: `extract_word_details` depends on `database` (for `DetailedWordRecord`). The `PayloadValidatorPort` protocol lives in `database` so there's no reverse dependency. The actual implementation of the port is owned by `extract_word_details` -- but `database` never imports it.

## Preconditions

- T1 completed: `DetailedWordRecord.payload` type is fixed, all `# type: ignore` removed, `make check` passes.

## Non-goals

- Implementing the actual validator adapter in `extract_word_details` (that would be done when the two packages are wired together at a higher level -- not in scope for this sprint).
- Making `payload_validator` required on `DetailedWordStore` -- it remains optional for backwards compatibility.
- Adding validation to the backend layer (`AbstractBackend` / `NeonBackend`).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/database/src/nl_processing/database/detailed_ports.py` -- add `PayloadValidatorPort`
- `packages/database/src/nl_processing/database/detailed_store.py` -- add `payload_validator` param, validate on read/write
- `packages/database/src/nl_processing/database/__init__.py` -- export `PayloadValidatorPort` if useful for downstream consumers
- `packages/database/tests/unit/database/` -- add validation unit tests
- `packages/database/tests/integration/database/` -- verify existing tests still pass (no changes expected)
- `packages/database/tests/e2e/database/` -- verify existing tests still pass (no changes expected)

**FORBIDDEN -- this task must NEVER touch:**

- `packages/extract_word_details/` -- do not implement the adapter
- `packages/database_cache/` -- not affected by this change
- `packages/core/`
- `docs/requirements/`, `docs/architecture/`

**Test scope:**

- `make check` in `packages/database/`

## Touched surface (expected files / modules)

- `packages/database/src/nl_processing/database/detailed_ports.py` -- new `PayloadValidatorPort` protocol
- `packages/database/src/nl_processing/database/detailed_store.py` -- new `__init__` param + validation calls
- `packages/database/tests/unit/database/test_detailed_store_get.py` or new file -- validation tests
- `packages/database/tests/unit/database/test_detailed_store_extract.py` or new file -- validation tests on write path

## Dependencies and sequencing notes

- Depends on T1 for the corrected payload type.
- Can run in parallel with T3 (which touches `database_cache` only).
- No downstream tasks depend on T2 within this sprint.

## Third-party / library research (mandatory for any external dependency)

- **Python `Protocol` (typing)**: Already used in the codebase (`detailed_ports.py` has `DetailedWordExtractorPort`). The `Protocol` + `@runtime_checkable` pattern is well-established.
  - Official docs: https://docs.python.org/3/library/typing.html#typing.Protocol
  - The existing `DetailedWordExtractorPort` is `@runtime_checkable` and serves as the exact pattern to follow.

- **Pydantic `ValidationError`**: The exceptions `SchemaVersionError` and `PayloadValidationError` are already defined in `packages/database/src/nl_processing/database/detailed_exceptions.py` and inherit from `DatabaseError`. No new exception classes needed.

## Implementation steps (developer-facing)

1. **Add `PayloadValidatorPort` to `detailed_ports.py`**:
   ```python
   @runtime_checkable
   class PayloadValidatorPort(Protocol):
       def validate_payload(
           self, schema_key: str, schema_version: int, payload: dict[str, JsonValue]
       ) -> None:
           """Raise if payload is invalid for the given schema.
           
           Raises:
               SchemaVersionError: If schema_key/version is unknown.
               PayloadValidationError: If payload doesn't match the schema.
           """
           ...
   ```
   Import `JsonValue` from `detailed_models` (or use the same type as `DetailedWordRecord.payload`). Import `runtime_checkable` (already imported in the file).

2. **Update `DetailedWordStore.__init__()` in `detailed_store.py`**:
   - Add `payload_validator: PayloadValidatorPort | None = None` parameter.
   - Store as `self._payload_validator = payload_validator`.
   - Import `PayloadValidatorPort` from `detailed_ports`.
   - Import `SchemaVersionError` and `PayloadValidationError` from `detailed_exceptions`.

3. **Add validation on the **write** path** in `get_or_extract_details()`:
   - After extraction (after line 120 `extracted_records = await self._extractor.extract(missing_words)`), before persisting each record, if `self._payload_validator is not None`:
     ```python
     self._payload_validator.validate_payload(
         record.schema_key, record.schema_version, record.payload
     )
     ```
   - If it raises `SchemaVersionError` or `PayloadValidationError`, let it propagate (do not catch).

4. **Add validation on the **read** path** in `get_details()`:
   - After constructing the `DetailedWordRecord` (after building `payload` from the DB row), if `self._payload_validator is not None`:
     ```python
     self._payload_validator.validate_payload(
         str(detail_row["schema_key"]),
         int(detail_row["schema_version"]),
         payload,
     )
     ```
   - Also add the same read validation in `get_or_extract_details()` where existing records are loaded from the `existing_lookup` dict (the second code path that builds `DetailedWordRecord` from cached rows).
   - If validation fails on read, let `SchemaVersionError` or `PayloadValidationError` propagate.

5. **Check file size**: After adding the validator wiring, `detailed_store.py` is currently 173 lines. Adding imports (~2 lines), the `__init__` param (~2 lines), and validation calls (~6-8 lines per path, 3 paths) could push it to ~195 lines. If it exceeds 200 lines, extract a private helper method `_validate_if_needed(schema_key, schema_version, payload)` to reduce repetition. If it exceeds 200 even after that, consider extracting the validation logic into a separate `_validation.py` module. The file must stay under 200 lines.

6. **Write unit tests for validation**:
   Create tests in the existing test files or a new `test_detailed_store_validation.py` file. Use a mock validator:

   ```python
   class FakeValidator:
       def __init__(self, error: Exception | None = None) -> None:
           self.calls: list[tuple[str, int, dict]] = []
           self._error = error

       def validate_payload(self, schema_key: str, schema_version: int, payload: dict) -> None:
           self.calls.append((schema_key, schema_version, payload))
           if self._error is not None:
               raise self._error
   ```

   Test cases:
   - **a)** `get_details()` with valid validator -- validator is called for each returned record, no error raised.
   - **b)** `get_details()` with validator raising `SchemaVersionError` -- error propagates.
   - **c)** `get_details()` with validator raising `PayloadValidationError` -- error propagates.
   - **d)** `get_or_extract_details()` with valid validator on extraction path -- validator is called for each extracted record before persistence.
   - **e)** `get_or_extract_details()` with validator raising error on extraction -- error propagates, record is NOT persisted.
   - **f)** `get_or_extract_details()` with valid validator on read path (existing records) -- validator is called.
   - **g)** No validator injected -- existing behavior unchanged, no validation calls.

7. **Verify existing tests pass**: All existing tests in `packages/database/tests/` create `DetailedWordStore` without `payload_validator`, so they exercise the "no validator" path. They must continue to pass unchanged.

8. **Run `make check` in `packages/database/`**: Must be 100% green.

## Production safety constraints (mandatory)

- **Database operations**: No database schema changes. Only Python logic changes in the store layer. Integration/e2e tests target the test database via `doppler run --`.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses existing `Protocol` pattern from `DetailedWordExtractorPort`. Reuses existing exception classes.
- **Correct file locations**: Changes confined to existing module files plus potentially one new test file.
- **No regressions**: The validator is optional. All existing callers that don't pass a validator continue to work identically.

## Error handling + correctness rules (mandatory)

- **Do not silence errors**: `SchemaVersionError` and `PayloadValidationError` must propagate to the caller.
- **No blanket try/catch**: The validator call must not be wrapped in a try/catch that swallows errors. Let exceptions propagate.
- **Fail fast**: If the validator rejects a payload on write, do NOT persist the record.

## Zero legacy tolerance rule (mandatory)

- `SchemaVersionError` and `PayloadValidationError` exception classes were defined in the previous sprint but never raised by any code path. After this task, they are raised by the validation path.
- No dead code remains.

## Acceptance criteria (testable)

1. `PayloadValidatorPort` protocol exists in `packages/database/src/nl_processing/database/detailed_ports.py` with `validate_payload(schema_key, schema_version, payload) -> None` signature.
2. `PayloadValidatorPort` is `@runtime_checkable`.
3. `DetailedWordStore.__init__()` accepts an optional `payload_validator: PayloadValidatorPort | None = None` parameter.
4. When a validator is injected and a record is read from DB, the validator is called with the record's `schema_key`, `schema_version`, and `payload`.
5. When a validator is injected and a record is extracted+persisted, the validator is called before persistence.
6. When the validator raises `SchemaVersionError`, the error propagates to the caller.
7. When the validator raises `PayloadValidationError`, the error propagates to the caller.
8. When no validator is injected, no validation occurs (existing behavior).
9. All existing tests pass unchanged (they don't inject a validator).
10. New unit tests cover scenarios (a) through (g) from step 6.
11. `make check` passes in `packages/database/` (unit + integration + e2e).
12. `detailed_store.py` remains under 200 lines.

## Verification / quality gates

- [x] Unit tests added/updated (new validation tests)
- [x] Integration/e2e tests pass (existing tests unchanged)
- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] Negative-path tests exist for `SchemaVersionError` and `PayloadValidationError` propagation
- [x] Task ends in a working, tested state

## Edge cases

- **Multiple records, one fails validation on read**: If `get_details([word_a, word_b])` is called and `word_a`'s record passes but `word_b`'s fails, the error should propagate immediately. No partial results.
- **Extracted record fails validation on write**: The extraction succeeded (LLM returned data) but the validator rejects it. The error propagates and the record is NOT persisted. This is the correct behavior per FM-7.
- **Validator raises unexpected exception**: If the validator raises something other than `SchemaVersionError` or `PayloadValidationError`, it should still propagate (fail-fast, no catch-all).

## Notes / risks

- **Risk**: Adding validation calls on every read path could impact performance. Mitigation: Validation is only called when a validator is injected. Integration tests run against real DB and will surface any performance issues.
- **Risk**: `detailed_store.py` could exceed 200 lines. Mitigation: Use a private helper method to deduplicate the validation call across the 3 code paths (2 in `get_or_extract_details`, 1 in `get_details`). If still over 200, extract validation into a separate helper module.
