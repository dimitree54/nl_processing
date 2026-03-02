---
Task ID: `T4`
Title: `Implement core exceptions with unit tests`
Sprint: `2026-03-02_module-core`
Module: `core`
Depends on: `T2`
Parallelizable: `yes, with T3, T5`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create `nl_processing/core/exceptions.py` with three typed exception classes — `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError` — and corresponding unit tests. After this task, all pipeline modules can import and raise these exceptions for consistent, typed error handling.

## Context (contract mapping)

- Requirements: `docs/planning-artifacts/prd.md` — CFR6 (`APIError`), CFR7 (`TargetLanguageNotFoundError`), CFR8 (`UnsupportedImageFormatError`), CFR9 (importable from core)
- Architecture: `docs/planning-artifacts/architecture.md` — "Error Handling Pattern", "Core Package = Shared Models + Exceptions + Helpers Only"
- Epics: `docs/planning-artifacts/epics.md` — Story 1.2: Core Exceptions

## Preconditions

- T1 completed — legacy cleanup done
- T2 completed — project dependencies are in place
- `nl_processing/core/__init__.py` exists (may be created by T3 running in parallel; if not, create it here — empty)

## Non-goals

- No error handling logic implementation — only exception class definitions
- No custom `__str__` or `__repr__` unless needed for `APIError` wrapping pattern
- No exception hierarchies beyond what is specified (3 flat exception classes)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/core/__init__.py` (create if not exists, must be empty)
- `nl_processing/core/exceptions.py` (create)
- `tests/unit/core/__init__.py` (create if not exists, must be empty)
- `tests/unit/core/test_exceptions.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `nl_processing/core/models.py` (T3)
- `nl_processing/core/prompts.py` (T5)
- `pyproject.toml`
- Any docs outside `docs/sprints/module-core/`

**Test scope:**
- Tests go in: `tests/unit/core/test_exceptions.py`
- Test command: `uv run pytest tests/unit/core/test_exceptions.py -x -v`

## Touched surface (expected files / modules)

- `nl_processing/core/__init__.py` — created if not exists, empty
- `nl_processing/core/exceptions.py` — created
- `tests/unit/core/__init__.py` — created if not exists, empty
- `tests/unit/core/test_exceptions.py` — created

## Dependencies and sequencing notes

- Depends on T2 (dependencies installed) — exceptions.py itself uses only stdlib, but being part of core, it should come after the project is in a clean dependency state
- Can run in parallel with T3 (models) and T5 (prompts) — no file overlap
- T7 depends on this task

## Third-party / library research (mandatory for any external dependency)

N/A — this task uses only Python stdlib `Exception` class. No third-party libraries.

## Implementation steps (developer-facing)

1. **Ensure `nl_processing/core/` directory exists** (may already exist from T3).
2. **Ensure `nl_processing/core/__init__.py`** exists and is empty.
3. **Create `nl_processing/core/exceptions.py`** with the following contents:
   ```python
   class APIError(Exception):
       """Wraps upstream OpenAI/LangChain API failures."""


   class TargetLanguageNotFoundError(Exception):
       """Raised when no text in the target language is detected."""


   class UnsupportedImageFormatError(Exception):
       """Raised when the image format is not supported by the OpenAI API."""
   ```
   Each exception is a direct subclass of `Exception` — no custom base class, no hierarchy between them. Each accepts a message string via standard `Exception.__init__`.
4. **Ensure `tests/unit/core/` directory exists**.
5. **Ensure `tests/unit/core/__init__.py`** exists and is empty.
6. **Create `tests/unit/core/test_exceptions.py`** with tests covering:
   - `APIError` can be raised and caught
   - `APIError` preserves message string: `str(APIError("msg")) == "msg"`
   - `APIError` can wrap another exception via `raise APIError("msg") from original_error` and `__cause__` is set
   - `TargetLanguageNotFoundError` can be raised and caught
   - `TargetLanguageNotFoundError` preserves message string
   - `UnsupportedImageFormatError` can be raised and caught
   - `UnsupportedImageFormatError` preserves message string
   - All three are subclasses of `Exception`
   - Each exception is a distinct type (catching one does not catch another)
7. **Run tests**: `uv run pytest tests/unit/core/test_exceptions.py -x -v`
8. **Run linting**: `uv run ruff format nl_processing/core/exceptions.py tests/unit/core/test_exceptions.py && uv run ruff check nl_processing/core/exceptions.py tests/unit/core/test_exceptions.py`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: No shared resources. Exception class definitions only.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using stdlib `Exception` — no custom exception frameworks.
- **Correct libraries only**: No third-party libraries needed.
- **Correct file locations**: `nl_processing/core/exceptions.py` per architecture spec.
- **No regressions**: New files — no existing functionality affected.

## Error handling + correctness rules (mandatory)

- Exception classes must not swallow or transform messages — pass through to `Exception.__init__`.
- Do not add default messages — callers provide the message.
- Do not add `__init__` unless needed (standard `Exception.__init__` is sufficient).

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — these are new files.
- Ensure no `__init__.py` re-exports.

## Acceptance criteria (testable)

1. `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError` succeeds
2. `raise APIError("test")` is caught by `except APIError`
3. `str(APIError("test")) == "test"`
4. `APIError` wrapping: `raise APIError("wrapped") from ValueError("original")` — `__cause__` is `ValueError`
5. `raise TargetLanguageNotFoundError("no Dutch")` is caught by `except TargetLanguageNotFoundError`
6. `raise UnsupportedImageFormatError(".bmp")` is caught by `except UnsupportedImageFormatError`
7. `except APIError` does NOT catch `TargetLanguageNotFoundError` or `UnsupportedImageFormatError`
8. `uv run pytest tests/unit/core/test_exceptions.py -x -v` passes
9. `uv run ruff check nl_processing/core/exceptions.py tests/unit/core/test_exceptions.py` passes
10. `nl_processing/core/exceptions.py` is under 200 lines

## Verification / quality gates

- [ ] Unit tests added in `tests/unit/core/test_exceptions.py`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (exception distinctness — catching one does not catch another)

## Edge cases

- Empty message string: `APIError("")` should work — empty string is a valid message.
- No-args construction: `APIError()` should work — standard `Exception` behavior.

## Rollout / rollback (if relevant)

- Rollout: Create files in a single commit.
- Rollback: Delete the created files.

## Notes / risks

- **Risk**: None significant. These are minimal exception classes with no external dependencies.
