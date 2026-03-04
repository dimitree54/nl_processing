---
Task ID: `T2`
Title: `Create database exceptions, models, and logging modules`
Sprint: `2026-03-04_database-and-sampling`
Module: `database`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

The database module has its foundational types: `ConfigurationError`, `DatabaseError` exceptions, `AddWordsResult`, `WordPair`, `ScoredWordPair` data models, and a structured logging setup. These are prerequisites for every other database file.

## Context (contract mapping)

- Requirements: `nl_processing/database/docs/prd_database.md` — FR16-FR17 (ConfigurationError), NFR8 (DatabaseError), FR7/FR11/FR34 (models)
- Architecture: `nl_processing/database/docs/architecture_database.md` — Module Internal Structure, exceptions.py, models.py, logging.py
- Shared architecture: `docs/planning-artifacts/architecture.md` — Error Handling Pattern, Naming Conventions

## Preconditions

- T1 complete (asyncpg dependency available)
- `nl_processing/database/__init__.py` exists (empty)

## Non-goals

- No backend code
- No service code
- No tests yet (models are trivial Pydantic/dataclass types)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `nl_processing/database/exceptions.py` — create
- `nl_processing/database/models.py` — create
- `nl_processing/database/logging.py` — create

**FORBIDDEN — this task must NEVER touch:**

- `nl_processing/database/__init__.py` (must stay empty per ruff)
- `nl_processing/database/service.py` (handled in T5)
- Any other module's code or tests
- `core/exceptions.py` (database exceptions are module-specific, not in core)

**Test scope:**

- No new tests in this task — models are trivial data containers
- `make check` must still pass with existing 26 tests

## Touched surface (expected files / modules)

- `nl_processing/database/exceptions.py` (new)
- `nl_processing/database/models.py` (new)
- `nl_processing/database/logging.py` (new)

## Dependencies and sequencing notes

- Depends on T1 for dependency availability
- T3-T14 all depend on types defined here

## Third-party / library research (mandatory for any external dependency)

- **Library**: Pydantic >=2.0 (already in project dependencies)
  - **Docs**: https://docs.pydantic.dev/latest/
  - `AddWordsResult` and `WordPair` are `BaseModel` subclasses
- **Library**: Python `logging` module (stdlib)
  - **Docs**: https://docs.python.org/3.12/library/logging.html
  - Used for structured logging with namespace `nl_processing.database`

## Implementation steps (developer-facing)

1. **Create `nl_processing/database/exceptions.py`:**
   - Define `ConfigurationError(Exception)` — raised when `DATABASE_URL` is missing
   - Define `DatabaseError(Exception)` — raised for database connectivity/operation failures
   - Keep file minimal — two classes, docstrings, nothing else

2. **Create `nl_processing/database/models.py`:**
   - Import `Word` from `nl_processing.core.models`
   - Define `AddWordsResult(BaseModel)` with fields: `new_words: list[Word]`, `existing_words: list[Word]`
   - Define `WordPair(BaseModel)` with fields: `source: Word`, `target: Word`
   - Define `ScoredWordPair(BaseModel)` with fields: `pair: WordPair`, `scores: dict[str, int]`
   - **Note on `dict[str, int]`**: This is the architecture-specified type for `ScoredWordPair.scores`. The ruff ban on `dict.get` applies to call sites, not type annotations. The dict maps exercise_type strings to integer scores — both key and value types are concrete.

3. **Create `nl_processing/database/logging.py`:**
   - Create a `get_logger(name: str)` function that returns `logging.getLogger(f"nl_processing.database.{name}")`
   - Keep minimal — just the factory function. Console handler is configured at application level, not module level.

4. Run `make check` — verify all 26 existing tests pass, no lint errors on new files.

## Production safety constraints (mandatory)

- **Database operations**: None — only type definitions.
- **Resource isolation**: No runtime resources.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `Word` from `core.models` — no reinvention.
- **Correct libraries only**: Pydantic (already in project), stdlib logging.
- **Correct file locations**: Matches architecture doc's Module Internal Structure exactly.
- **No regressions**: No existing code modified.

## Error handling + correctness rules (mandatory)

- Exceptions are concrete types with clear names — no generic catch-all.
- No silent fallbacks in exception definitions.

## Zero legacy tolerance rule (mandatory)

- No old code paths affected — these are new files.

## Acceptance criteria (testable)

1. `nl_processing/database/exceptions.py` defines `ConfigurationError` and `DatabaseError` as `Exception` subclasses.
2. `nl_processing/database/models.py` defines `AddWordsResult`, `WordPair`, `ScoredWordPair` as Pydantic `BaseModel` subclasses with correct field types.
3. `nl_processing/database/logging.py` defines `get_logger(name: str)` returning a `logging.Logger`.
4. All three files are under 200 lines.
5. `from nl_processing.database.exceptions import ConfigurationError, DatabaseError` succeeds.
6. `from nl_processing.database.models import AddWordsResult, WordPair, ScoredWordPair` succeeds.
7. `make check` passes.

## Verification / quality gates

- [ ] All three files created with correct content
- [ ] Files pass ruff format + ruff check
- [ ] Files under 200 lines each
- [ ] `make check` passes (26 tests + linters)
- [ ] vulture does not flag new symbols (they'll be used by subsequent tasks)

## Edge cases

- `ScoredWordPair.scores` uses `dict[str, int]` — ruff bans `dict.get()` at call sites, but the type annotation itself is fine.
- vulture may flag new symbols as unused until subsequent tasks import them. If so, add temporary whitelist entries or accept that vulture runs against the whole codebase and these symbols will be used soon.

## Notes / risks

- **Risk**: vulture flags newly created classes as unused.
  - **Mitigation**: vulture should not flag them if they're importable symbols in non-test files. If flagged, add to `vulture_whitelist.py` temporarily — T5+ will use them. Note: check vulture behavior — it may not flag classes in library code that aren't called from the same codebase yet. If it does, add whitelist entries in this task.
