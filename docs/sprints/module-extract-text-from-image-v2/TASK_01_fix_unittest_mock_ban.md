---
Task ID: `T1`
Title: `Fix banned unittest.mock.AsyncMock imports in test files`
Sprint: `2026-03-03_extract-text-v2-modifications`
Module: `extract_text_from_image`
Depends on: `—`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Remove all `from unittest.mock import AsyncMock` imports from the two test files that cause `make check` to fail due to ruff rule TID251. Replace with an equivalent async mock pattern that does not import from `unittest`.

## Context (contract mapping)

- Requirements: `ruff.toml` lines 54-57 — `unittest`, `unittest.TestCase`, `unittest.mock` are all banned
- Architecture: `docs/planning-artifacts/architecture.md` § "Import discipline" — "No `unittest` — use pytest (enforced by ruff ban)"

## Preconditions

- None. This is the first task.

## Non-goals

- Do not install `pytest-mock` or add new dependencies to `pyproject.toml`.
- Do not change test logic or coverage — only replace the mock mechanism.
- Do not modify `service.py` or any production code.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — fix banned import
- `tests/unit/extract_text_from_image/test_error_handling.py` — fix banned import

**FORBIDDEN — this task must NEVER touch:**
- Any production code (`nl_processing/`)
- Any other test files
- `pyproject.toml` (no new dependencies)

**Test scope:**
- Tests go in: `tests/unit/extract_text_from_image/`
- Test command: `uv run pytest tests/unit/extract_text_from_image/ -x -v`
- Lint command: `uv run ruff check tests/unit/extract_text_from_image/`

## Touched surface (expected files / modules)

- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` (line 4: `from unittest.mock import AsyncMock`)
- `tests/unit/extract_text_from_image/test_error_handling.py` (line 3: `from unittest.mock import AsyncMock`)

## Dependencies and sequencing notes

- No dependencies. This is the first task.
- Must complete before T2 because T2 also modifies test files and we need a clean lint baseline.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. This task uses only Python stdlib and pytest built-ins.

**AsyncMock replacement approach — research results:**

`pytest-mock` is NOT installed (verified: `import pytest_mock` raises `ModuleNotFoundError`). We cannot use it.

**Solution**: Replace `AsyncMock` with a lightweight mock class defined in the test file. The pattern:

```python
from types import SimpleNamespace

class _AsyncChainMock:
    """Minimal async mock for LangChain chain, replacing unittest.mock.AsyncMock."""

    def __init__(self, return_value: SimpleNamespace) -> None:
        self.ainvoke_calls: list[dict[str, list[object]]] = []
        self._return_value = return_value

    async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
        self.ainvoke_calls.append(input_dict)
        return self._return_value
```

This replaces the 3 things AsyncMock provided:
1. `extractor._chain = AsyncMock()` → `extractor._chain = _AsyncChainMock(response)`
2. `extractor._chain.ainvoke = AsyncMock(return_value=...)` → already wired in constructor
3. `extractor._chain.ainvoke.call_count` → `len(extractor._chain.ainvoke_calls)`
4. `extractor._chain.ainvoke.call_args[0][0]` → `extractor._chain.ainvoke_calls[0]`
5. `extractor._chain.ainvoke.call_args_list` → `extractor._chain.ainvoke_calls`

For the `side_effect` pattern (raising exceptions), add an `_exception` parameter:

```python
class _AsyncChainMockError:
    """Async mock that raises an exception on ainvoke."""

    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
        raise self._exception
```

## Implementation steps (developer-facing)

### File 1: `tests/unit/extract_text_from_image/test_extract_text_from_image.py`

1. **Remove** line 4: `from unittest.mock import AsyncMock`

2. **Add** a helper class at the top of the file (after imports, before `_make_tool_response`):

   ```python
   class _AsyncChainMock:
       """Async mock for the LangChain chain — replaces unittest.mock.AsyncMock."""

       def __init__(self, return_value: SimpleNamespace) -> None:
           self.ainvoke_calls: list[dict[str, list[object]]] = []
           self._return_value = return_value

       async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
           self.ainvoke_calls.append(input_dict)
           return self._return_value
   ```

3. **Replace** every occurrence of the pattern:
   ```python
   extractor._chain = AsyncMock()
   extractor._chain.ainvoke = AsyncMock(return_value=_make_tool_response(expected_text))
   ```
   With:
   ```python
   extractor._chain = _AsyncChainMock(_make_tool_response(expected_text))
   ```

4. **Replace** assertion patterns:
   - `extractor._chain.ainvoke.call_args[0][0]` → `extractor._chain.ainvoke_calls[0]`
   - `extractor._chain.ainvoke.call_count` → `len(extractor._chain.ainvoke_calls)`
   - `extractor._chain.ainvoke.call_args_list` → `extractor._chain.ainvoke_calls` (iterate directly, each item is the input_dict)

5. **Verify** each test function still exercises the same assertions.

### File 2: `tests/unit/extract_text_from_image/test_error_handling.py`

1. **Remove** line 3: `from unittest.mock import AsyncMock`

2. **Add** two helper classes:

   ```python
   class _AsyncChainMock:
       """Async mock for the LangChain chain — replaces unittest.mock.AsyncMock."""

       def __init__(self, return_value: SimpleNamespace) -> None:
           self.ainvoke_calls: list[dict[str, list[object]]] = []
           self._return_value = return_value

       async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
           self.ainvoke_calls.append(input_dict)
           return self._return_value


   class _AsyncChainMockError:
       """Async mock that raises an exception on ainvoke."""

       def __init__(self, exception: Exception) -> None:
           self._exception = exception

       async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
           raise self._exception
   ```

3. **Replace** the `_setup_extractor_with_mock_chain` helper to use `_AsyncChainMock`:
   ```python
   extractor._chain = _AsyncChainMock(_make_tool_response(mock_text_response))
   ```
   (Remove the two-line `AsyncMock()` + `AsyncMock(return_value=...)` pattern.)

4. **Replace** all `side_effect` mocks with `_AsyncChainMockError`:
   - `extractor._chain = AsyncMock(); extractor._chain.ainvoke = AsyncMock(side_effect=RuntimeError("API failed"))` → `extractor._chain = _AsyncChainMockError(RuntimeError("API failed"))`
   - Same for the loop in `test_api_error_wrapping_various_exceptions` — update to `extractor._chain = _AsyncChainMockError(original_exception)`
   - Same for `test_api_error_wrapping_cv2_path`

5. **Note about code duplication**: The `_AsyncChainMock` and `_AsyncChainMockError` classes appear in both files. This is acceptable because:
   - They are small (< 10 lines each)
   - They are test-only helpers
   - Extracting to a shared conftest would be premature for 2 files
   - `jscpd` checks for copy-paste at a threshold, and these are small enough to pass

### Verification

6. Run `uv run ruff check tests/unit/extract_text_from_image/` — must pass with zero TID251 errors.
7. Run `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests must pass.

## Production safety constraints (mandatory)

- No production code is modified.
- No database operations.
- No shared resources affected.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Using plain Python classes to mock async behavior — simplest possible approach.
- **Correct libraries only**: No new libraries. Python stdlib `types.SimpleNamespace` already used in the files.
- **Correct file locations**: Test files stay in their existing locations.
- **No regressions**: Every existing test must pass with identical behavior.

## Error handling + correctness rules (mandatory)

- The `_AsyncChainMockError` class re-raises the exception directly — no swallowing.
- No try/except added to test code.

## Zero legacy tolerance rule (mandatory)

- The `from unittest.mock import AsyncMock` import line is **removed**, not commented out.
- No `AsyncMock` references remain in either file.

## Acceptance criteria (testable)

1. `from unittest.mock import AsyncMock` does NOT appear in `tests/unit/extract_text_from_image/test_extract_text_from_image.py`
2. `from unittest.mock import AsyncMock` does NOT appear in `tests/unit/extract_text_from_image/test_error_handling.py`
3. `uv run ruff check tests/unit/extract_text_from_image/` passes with zero errors
4. `uv run pytest tests/unit/extract_text_from_image/ -x -v` passes — all tests green
5. No `unittest` string appears anywhere in either file (no residual imports)

## Verification / quality gates

- [ ] `uv run ruff check tests/unit/extract_text_from_image/` — zero errors
- [ ] `uv run pytest tests/unit/extract_text_from_image/ -x -v` — all tests pass
- [ ] Grep both files for `unittest` — zero matches
- [ ] No new warnings introduced

## Edge cases

- `test_api_error_wrapping_various_exceptions` iterates over multiple exceptions in a loop, replacing the chain mock each iteration. The `_AsyncChainMockError` approach handles this naturally — create a new instance per iteration.
- `test_both_methods_converge_to_chain` checks `call_count == 2` and iterates `call_args_list` — must verify the `ainvoke_calls` list accumulates correctly across two calls.

## Notes / risks

- **Risk**: The `_AsyncChainMock` class might not replicate all behaviors of `AsyncMock` (e.g., attribute access tracking).
  - **Mitigation**: The tests only use `.ainvoke()`, `.ainvoke.call_args`, `.ainvoke.call_count`, `.ainvoke.call_args_list`, and `side_effect`. All are covered by the replacement classes.
- **Risk**: Duplicate mock classes across 2 files may trigger `jscpd`.
  - **Mitigation**: The classes are small (< 10 lines). If `jscpd` flags it, extract to `tests/unit/extract_text_from_image/conftest.py`. But try without extraction first.
