---
Sprint ID: `2026-03-13_fix-detailed-word-debt`
Sprint Goal: Resolve all tech debt and type mismatches in the detailed-word persistence layer across `database`, `database_cache`, and `extract_word_details`.
Sprint Type: module
Module: database, database_cache, extract_word_details
---

## Goal

Fix the `DetailedWordRecord.payload` type to accept arbitrarily nested JSON structures from POS models, remove all `# type: ignore` workarounds, implement FR-14 payload validation via a `PayloadValidatorPort` protocol, and add missing `@runtime_checkable` decorators in `database_cache`. After this sprint, all three packages pass `make check` including integration tests that call the real OpenAI API.

## Module Scope

### What this sprint implements

- **`database`** -- Fix `DetailedWordRecord.payload` type, add `PayloadValidatorPort` protocol, wire validation into `DetailedWordStore` on read/write, remove `# type: ignore` comments, add validation unit tests.
- **`database_cache`** -- Add `@runtime_checkable` to `RemoteDetailedWordStorePort` and `SchemaVersionChecker` protocols.
- **`extract_word_details`** -- No source changes expected (serializer already returns `dict[str, object]`). Integration tests should pass once the payload type is fixed.

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED -- this sprint may ONLY touch:**

- `packages/database/src/nl_processing/database/detailed_models.py` -- payload type fix
- `packages/database/src/nl_processing/database/detailed_store.py` -- remove type ignores, add validation
- `packages/database/src/nl_processing/database/detailed_ports.py` -- add `PayloadValidatorPort`
- `packages/database/src/nl_processing/database/__init__.py` -- export new port if needed
- `packages/database/tests/` -- update/add tests
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py` -- add `@runtime_checkable`
- `packages/database_cache/tests/` -- update tests if payload type changes affect them
- `packages/extract_word_details/tests/` -- verify integration tests pass (no source changes expected)

**FORBIDDEN -- this sprint must NEVER touch:**

- `docs/requirements/`, `docs/architecture/` -- do not modify specs
- `packages/core/` -- do not modify core models
- `packages/translate_word/`, `packages/sampling/` -- unrelated modules
- Root configs (`Makefile`, `pyproject.toml`, `ruff.toml`) -- already correct
- Any bot-level code or handlers

### Test Scope

- **`database`**: `make check` in `packages/database/` (unit + integration + e2e)
- **`database_cache`**: `make check` in `packages/database_cache/` (unit + integration + e2e)
- **`extract_word_details`**: `make check` in `packages/extract_word_details/` (unit + integration + e2e)
- **NEVER run** the global `make check` during individual task verification.

## Interface Contract

### Public interfaces unchanged by this sprint

```python
# database — signatures unchanged, payload type widens
class DetailedWordStore:
    def __init__(self, *, source_language: Language, target_language: Language,
                 backend: AbstractBackend | None = None,
                 extractor: DetailedWordExtractorPort | None = None,
                 payload_validator: PayloadValidatorPort | None = None) -> None: ...
    async def get_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...
    async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]: ...

# database — NEW protocol
class PayloadValidatorPort(Protocol):
    def validate_payload(self, schema_key: str, schema_version: int,
                         payload: dict[str, JsonValue]) -> None: ...
```

### Model change

```python
# DetailedWordRecord.payload type changes from:
payload: dict[str, str | int | bool | list[str] | dict[str, str]]
# to:
payload: dict[str, JsonValue]
# where JsonValue is a recursive type alias for arbitrary JSON
```

## Scope

### In

- Fix `DetailedWordRecord.payload` type to accept nested JSON structures
- Remove all `# type: ignore[assignment]` comments from `detailed_store.py`
- Add `PayloadValidatorPort` protocol to `database/detailed_ports.py`
- Wire `PayloadValidatorPort` into `DetailedWordStore` for read/write validation
- Add `@runtime_checkable` to `database_cache` protocols
- Add unit tests for validation behavior (valid, invalid schema, invalid payload)
- Verify all integration/e2e tests pass across all three packages

### Out

- New features, new POS models, new language pairs
- Cache eviction, migration tooling
- Changes to `core` package
- Changes to requirements or architecture docs

## Inputs (contracts)

- `packages/database/docs/module-spec.md` -- FR-14, BR-9, NFR-4, CR-4, FM-7
- `packages/database_cache/docs/module-spec.md` -- FR-11 through FR-15
- `packages/extract_word_details/docs/module-spec.md` -- FR-1 through FR-11
- Previous sprint: `docs/sprints/extract-word-details/SPRINT.md`

## Change digest

- **Requirement deltas**: No spec changes. This sprint resolves implementation gaps against existing FR-14, BR-9, NFR-4, CR-4, FM-7.

## Task list (dependency-aware)

- **T1:** [`TASK_01.md`](TASK_01.md) (depends: --) -- Fix payload type + remove type ignores + verify all tests pass
- **T2:** [`TASK_02.md`](TASK_02.md) (depends: T1) (parallel: yes, with T3) -- Add `PayloadValidatorPort` + wire validation into `DetailedWordStore` + unit tests
- **T3:** [`TASK_03.md`](TASK_03.md) (depends: T1) (parallel: yes, with T2) -- Add `@runtime_checkable` to `database_cache` protocols + verify tests

## Dependency graph (DAG)

```
T1 --> T2
T1 --> T3
```

## Execution plan

### Critical path

T1 --> T2

### Parallel tracks (lanes)

- **Lane A**: T1, T2 (payload fix then validation)
- **Lane B**: T3 (runtime_checkable, independent after T1)

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. All development uses testing/development databases via Doppler-managed `DATABASE_URL`.
- **Shared resource isolation**: Integration/e2e tests run under `doppler run --` which injects the test-database credentials. No schema changes are introduced -- only type annotations and runtime validation logic change. The `word_details_nl_ru` table schema in PostgreSQL is untouched.

## Definition of Done (DoD)

All items must be true:

- `make check` passes in `packages/database/` (unit + integration + e2e)
- `make check` passes in `packages/database_cache/` (unit + integration + e2e)
- `make check` passes in `packages/extract_word_details/` (unit + integration + e2e)
- Zero `# type: ignore` comments remain in `detailed_store.py`
- `PayloadValidatorPort` exists in `database/detailed_ports.py`
- `DetailedWordStore` validates payloads on read and write when a validator is injected
- `SchemaVersionError` and `PayloadValidationError` are raised by validation path (not just defined)
- `@runtime_checkable` decorates both protocols in `database_cache/detailed_ports.py`
- Module isolation: no files outside the ALLOWED list were touched
- No errors silenced: no empty catch, no blanket try/catch discarding exceptions
- Requirements/architecture docs unchanged
- Production database untouched

## Risks + mitigations

- **Risk**: `dict[str, object]` or a `JsonValue` recursive type alias may trigger the ruff `builtins.object` ban.
  - **Mitigation**: T1 explicitly requires the developer to check ruff output. The ban targets standalone `object` type annotations, not `object` as a type parameter. If ruff does flag it, fall back to the recursive `JsonValue` type alias defined locally in `detailed_models.py`.

- **Risk**: Widening the payload type could mask actual type errors in tests.
  - **Mitigation**: FR-14 validation (T2) compensates by adding runtime schema validation on read/write. The real type safety comes from `parse_payload()` via the schema registry, not from the dict value type.

- **Risk**: Existing tests in `database_cache` use simple `{"definition": "..."}` payloads that already conform to the old type.
  - **Mitigation**: These tests should continue to work unchanged since the type is widened, not narrowed.

## Sources used

- `packages/database/docs/module-spec.md`
- `packages/database_cache/docs/module-spec.md`
- `packages/extract_word_details/docs/module-spec.md`
- `packages/database/src/nl_processing/database/detailed_models.py`
- `packages/database/src/nl_processing/database/detailed_store.py`
- `packages/database/src/nl_processing/database/detailed_ports.py`
- `packages/database/src/nl_processing/database/detailed_exceptions.py`
- `packages/database/tests/unit/database/mock_backend.py`
- `packages/database/tests/unit/database/test_detailed_models.py`
- `packages/database/tests/unit/database/test_detailed_store_get.py`
- `packages/database/tests/unit/database/test_detailed_store_extract.py`
- `packages/database/tests/integration/database/test_detailed_integration.py`
- `packages/database/tests/e2e/database/test_detailed_full_flow.py`
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`
- `packages/database_cache/tests/unit/database_cache/detailed_mocks.py`
- `packages/database_cache/tests/unit/database_cache/test_detailed_schema_failures.py`
- `packages/extract_word_details/src/nl_processing/extract_word_details/_serializer.py`
- `packages/extract_word_details/src/nl_processing/extract_word_details/service.py`
- `packages/extract_word_details/tests/integration/extract_word_details/test_live_extraction.py`
- Root `ruff.toml`, root `Makefile`

## Contract summary

### What (requirements)

- FR-14: Reject missing source words, unsupported schema versions, and invalid payloads
- BR-9: Detailed-word rows store only schema-validated payloads
- NFR-4: Detailed-word payloads never bypass typed validation
- CR-4: Round-trip through extractor-owned schema registry
- FM-7: Schema mismatch raises explicit error

### How (architecture)

- Widen `DetailedWordRecord.payload` to `dict[str, JsonValue]` using a recursive type alias
- Define `PayloadValidatorPort` protocol to avoid circular `database` -> `extract_word_details` dependency
- Inject optional validator into `DetailedWordStore.__init__()`
- Validate on write (before `upsert_word_details`) and on read (after loading from DB)
- Add `@runtime_checkable` to `database_cache` protocols for consistency

## Impact inventory (implementation-facing)

- **Module**: `database` (`packages/database/`) -- model, store, ports, tests
- **Module**: `database_cache` (`packages/database_cache/`) -- ports only
- **Module**: `extract_word_details` (`packages/extract_word_details/`) -- tests only (verify pass)
- **Interfaces**: `DetailedWordStore.__init__()` gains optional `payload_validator` param
- **Data model**: No SQL schema changes; only Python type annotations
- **External services**: OpenAI API (integration tests), Neon PostgreSQL (integration/e2e tests)
- **Test directories**: `packages/database/tests/`, `packages/database_cache/tests/`, `packages/extract_word_details/tests/`
