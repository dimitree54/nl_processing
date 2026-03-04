---
Task ID: `T3`
Title: `Create abstract backend ABC for database operations`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The `AbstractBackend` ABC defines the contract for all database operations. This enables the `DatabaseService` to be backend-agnostic and allows future backend swaps (e.g., if Neon latency exceeds the 200ms threshold).

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — "Backend abstraction" in Core Features
- Architecture: `nl_processing/database/docs/architecture_database.md` — Decision: Abstract Backend Interface (full method signatures)

## Preconditions

- T2 complete (exceptions and models exist)
- `nl_processing/database/` exists with `__init__.py`

## Non-goals

- No concrete implementation (that's T4)
- No tests (ABC is not testable standalone)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/backend/` — create directory
- `nl_processing/database/backend/__init__.py` — create (empty)
- `nl_processing/database/backend/abstract.py` — create

**FORBIDDEN — this task must NEVER touch:**

- Any other module's code or tests
- `nl_processing/database/service.py`
- `nl_processing/database/__init__.py`

**Test scope:**

- No new tests — ABC cannot be tested standalone
- `make check` must pass with existing 26 tests

## Touched surface (expected files / modules)

- `nl_processing/database/backend/__init__.py` (new, empty)
- `nl_processing/database/backend/abstract.py` (new)

## Dependencies and sequencing notes

- Depends on T2 for type availability (though abstract.py uses primitives, not models)
- T4 depends on this for the ABC to implement

## Third-party / library research (mandatory for any external dependency)

- **Library**: Python `abc` module (stdlib)
  - **Docs**: https://docs.python.org/3.12/library/abc.html
  - `ABC` base class and `@abstractmethod` decorator

## Implementation steps (developer-facing)

1. **Create `nl_processing/database/backend/` directory.**

2. **Create `nl_processing/database/backend/__init__.py`** — empty file (enforced by ruff).

3. **Create `nl_processing/database/backend/abstract.py`:**
   - Import `ABC`, `abstractmethod` from `abc`
   - Define `AbstractBackend(ABC)` with the following abstract methods (all `async def`):
     - `add_word(self, table: str, normalized_form: str, word_type: str) -> int | None` — insert word if not exists, return row id or None if already exists
     - `get_word(self, table: str, normalized_form: str) -> dict[str, str | int] | None` — return row dict or None
     - `add_translation_link(self, table: str, source_id: int, target_id: int) -> None`
     - `get_user_words(self, user_id: str, language: str, word_type: str | None = None, limit: int | None = None, random: bool = False) -> list[dict[str, str | int]]`
     - `add_user_word(self, user_id: str, word_id: int, language: str) -> None`
     - `increment_user_exercise_score(self, table: str, user_id: str, source_word_id: int, exercise_type: str, delta: int) -> int` — returns new score
     - `get_user_exercise_scores(self, table: str, user_id: str, source_word_ids: list[int], exercise_types: list[str]) -> list[dict[str, str | int]]`
     - `create_tables(self, languages: list[str], pairs: list[tuple[str, str]]) -> None`
   - Add docstrings to each method
   - **Important**: Backend methods operate on primitives (`str`, `int`, `dict`), NOT on `Word` models. The service layer handles model↔primitive conversion.
   - **Note on `dict` types**: Use `dict[str, str | int]` as the return type for row dicts. This is more specific than bare `dict` while staying flexible for different column types. Access dict values with `[]` (not `.get()`), consistent with project rules.

4. Run `make check` — verify no lint issues and existing tests pass.

## Production safety constraints (mandatory)

- **Database operations**: None — only ABC definition.
- **Resource isolation**: No runtime resources.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using stdlib `abc` — no external dependencies.
- **Correct file locations**: `backend/abstract.py` matches architecture doc layout exactly.
- **No regressions**: New files only.

## Error handling + correctness rules (mandatory)

- Abstract methods declare return types clearly — implementors know what to return.
- No default implementations that swallow errors.

## Zero legacy tolerance rule (mandatory)

- No old code paths affected.

## Acceptance criteria (testable)

1. `nl_processing/database/backend/__init__.py` exists and is empty.
2. `nl_processing/database/backend/abstract.py` defines `AbstractBackend(ABC)` with all 8 abstract methods matching the architecture spec signatures.
3. All methods are decorated with `@abstractmethod`.
4. All methods are `async def`.
5. File is under 200 lines.
6. `from nl_processing.database.backend.abstract import AbstractBackend` succeeds.
7. `make check` passes.

## Verification / quality gates

- [ ] ABC created with all methods
- [ ] All methods are abstract and async
- [ ] File passes ruff format + check
- [ ] File under 200 lines
- [ ] `make check` passes (26 tests)

## Edge cases

- `get_user_words` has optional parameters (`word_type`, `limit`, `random`) — these must have default values in the abstract signature.

## Notes / risks

- **Risk**: Method signatures may need adjustment during implementation.
  - **Mitigation**: Architecture doc provides exact signatures. Any deviation would require a change proposal.
