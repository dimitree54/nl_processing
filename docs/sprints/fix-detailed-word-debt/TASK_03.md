---
Task ID: T3
Title: Add `@runtime_checkable` to `database_cache` protocols
Sprint: `2026-03-13_fix-detailed-word-debt`
Module: database_cache
Depends on: T1
Parallelizable: yes, with T2
---

## Goal / value

After this task, `RemoteDetailedWordStorePort` and `SchemaVersionChecker` in `database_cache/detailed_ports.py` are decorated with `@runtime_checkable`, consistent with `DetailedWordExtractorPort` in `database/detailed_ports.py`. This allows runtime `isinstance()` checks to verify port satisfaction, matching the established codebase pattern.

## Context (contract mapping)

- `packages/database/src/nl_processing/database/detailed_ports.py` line 10-11: `@runtime_checkable` on `DetailedWordExtractorPort` -- established pattern.
- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`: Both `RemoteDetailedWordStorePort` and `SchemaVersionChecker` are plain `Protocol` without `@runtime_checkable` -- inconsistency.

## Preconditions

- T1 completed: payload type is fixed and `make check` passes in `database_cache`.

## Non-goals

- Adding new methods or changing signatures on the protocols.
- Adding `isinstance()` checks to any implementation code (just enabling them).
- Modifying tests beyond adding `isinstance()` verification tests if useful.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**

- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py` -- add `@runtime_checkable`
- `packages/database_cache/tests/` -- optionally add `isinstance()` verification tests

**FORBIDDEN -- this task must NEVER touch:**

- `packages/database/` -- not affected
- `packages/extract_word_details/` -- not affected
- `packages/core/`
- `docs/requirements/`, `docs/architecture/`

**Test scope:**

- `make check` in `packages/database_cache/`

## Touched surface (expected files / modules)

- `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py` (2-3 lines changed)
- Optionally `packages/database_cache/tests/unit/database_cache/` (new or extended test for `isinstance` checks)

## Dependencies and sequencing notes

- Depends on T1 only because T1 fixes the payload type used in the protocols' method signatures (via `DetailedWordRecord`). If T1 changed the payload type in `DetailedWordRecord`, any tests constructing records in `database_cache` must already work.
- Can run in parallel with T2 (which only touches `database` package).

## Third-party / library research (mandatory for any external dependency)

- **`typing.runtime_checkable`**: Standard library decorator. When applied to a `Protocol` subclass, it allows `isinstance()` and `issubclass()` checks at runtime. Without it, `isinstance(obj, SomeProtocol)` raises `TypeError`.
  - Official docs: https://docs.python.org/3/library/typing.html#typing.runtime_checkable
  - Already imported and used in `packages/database/src/nl_processing/database/detailed_ports.py` line 3.
  - Limitation: `isinstance()` only checks method existence, not signatures. This is a known Python limitation and acceptable.

## Implementation steps (developer-facing)

1. **Edit `packages/database_cache/src/nl_processing/database_cache/detailed_ports.py`**:
   - Add `runtime_checkable` to the import: change `from typing import Protocol` to `from typing import Protocol, runtime_checkable`.
   - Add `@runtime_checkable` decorator above `class RemoteDetailedWordStorePort(Protocol):`.
   - Add `@runtime_checkable` decorator above `class SchemaVersionChecker(Protocol):`.

   The file should look like:
   ```python
   """Protocols for remote detailed word store and schema checker."""

   from typing import Protocol, runtime_checkable

   from nl_processing.core.models import Word
   from nl_processing.database.detailed_models import DetailedWordRecord


   @runtime_checkable
   class RemoteDetailedWordStorePort(Protocol):
       """Protocol for remote detailed word store backend."""

       async def get_or_extract_details(self, words: list[Word]) -> list[DetailedWordRecord]:
           """Fetch detailed word records from remote store."""


   @runtime_checkable
   class SchemaVersionChecker(Protocol):
       """Protocol for checking schema version compatibility."""

       def is_compatible(self, schema_key: str, schema_version: int) -> bool:
           """Check if a schema version is compatible with current registry."""
   ```

2. **Optionally add isinstance verification tests**: If not already tested, add a small test in `packages/database_cache/tests/unit/database_cache/` that verifies the mock classes satisfy the protocol:

   ```python
   from tests.unit.database_cache.detailed_mocks import MockRemoteDetailedWordStore, MockSchemaChecker
   from nl_processing.database_cache.detailed_ports import RemoteDetailedWordStorePort, SchemaVersionChecker

   def test_mock_remote_store_satisfies_protocol() -> None:
       assert isinstance(MockRemoteDetailedWordStore(), RemoteDetailedWordStorePort)

   def test_mock_schema_checker_satisfies_protocol() -> None:
       assert isinstance(MockSchemaChecker(), SchemaVersionChecker)
   ```

   This follows the exact pattern from `packages/database/tests/unit/database/test_detailed_models.py` lines 68-86 where `DetailedWordExtractorPort` is verified with `isinstance()`.

3. **Run `make check` in `packages/database_cache/`**: Must be 100% green.

## Production safety constraints (mandatory)

- **Database operations**: No database operations. Only a decorator addition to Protocol classes.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Following the exact pattern from `database/detailed_ports.py`.
- **Correct file locations**: Only modifying the existing ports file.
- **No regressions**: Adding `@runtime_checkable` to a Protocol is purely additive. It does not change existing behavior -- it only enables `isinstance()` checks that were previously impossible.

## Error handling + correctness rules (mandatory)

- No error handling changes. This is a pure annotation change.

## Zero legacy tolerance rule (mandatory)

- The inconsistency between `database/detailed_ports.py` (has `@runtime_checkable`) and `database_cache/detailed_ports.py` (missing it) is resolved.

## Acceptance criteria (testable)

1. `RemoteDetailedWordStorePort` in `database_cache/detailed_ports.py` has `@runtime_checkable` decorator.
2. `SchemaVersionChecker` in `database_cache/detailed_ports.py` has `@runtime_checkable` decorator.
3. `isinstance(MockRemoteDetailedWordStore(), RemoteDetailedWordStorePort)` returns `True`.
4. `isinstance(MockSchemaChecker(), SchemaVersionChecker)` returns `True`.
5. `isinstance(object(), RemoteDetailedWordStorePort)` returns `False` (non-conforming class).
6. `make check` passes in `packages/database_cache/` (unit + integration + e2e).

## Verification / quality gates

- [x] Unit tests added/updated (optional isinstance verification tests)
- [x] Integration/e2e tests pass (existing tests unchanged)
- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] Task ends in a working, tested state

## Edge cases

- **Protocol with only async methods**: `RemoteDetailedWordStorePort` has only an async method. `isinstance()` checks with `@runtime_checkable` only verify method existence, not that the method is async. This is acceptable per Python's Protocol semantics.

## Notes / risks

- **Risk**: None significant. This is a minimal 2-3 line change with no behavioral impact on existing code.
