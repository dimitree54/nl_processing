---
Task ID: `T5`
Title: `Create unit tests`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T3, T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create comprehensive unit tests for the `extract_text_from_image` module covering: image encoding logic (path → base64, cv2 → base64), format validation, error mapping (UnsupportedImageFormatError, TargetLanguageNotFoundError, APIError wrapping), and the happy-path extraction flow with a mocked LangChain chain. After this task, all module logic is validated without making any real API calls.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — all ETI-FRs (validated via unit tests)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — "Test Strategy" (unit tests mock LangChain chain)
- Shared: `docs/planning-artifacts/architecture.md` — test organization, no `unittest`, use pytest

## Preconditions

- T2 completed — `service.py`, `image_encoding.py`, `prompts/nl.json` exist
- T3 completed — error handling implemented
- T4 completed — `benchmark.py` exists (needed for `generate_test_image` to create test fixtures)
- Module-core sprint complete — `core.models`, `core.exceptions` available

## Non-goals

- No real API calls — all LLM interactions are mocked
- No integration or e2e tests — that is T6
- No testing of benchmark utilities themselves (they are dev tools; their correctness is validated by their usage in integration tests)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/unit/extract_text_from_image/__init__.py` (exists — keep)
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` (create — new test file, old one was deleted in T1)
- `tests/unit/extract_text_from_image/test_image_encoding.py` (create)
- `tests/unit/extract_text_from_image/test_error_handling.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/` (any source code — tests only)
- `tests/unit/core/` (owned by module-core sprint)
- `tests/integration/`, `tests/e2e/` (T6)
- `pyproject.toml`
- Any docs outside `docs/sprints/module-extract-text-from-image/`

**Test scope:**
- Tests go in: `tests/unit/extract_text_from_image/`
- Test command: `uv run pytest tests/unit/extract_text_from_image/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` — main service tests (mocked chain)
- `tests/unit/extract_text_from_image/test_image_encoding.py` — encoding and format validation tests
- `tests/unit/extract_text_from_image/test_error_handling.py` — error path tests

## Dependencies and sequencing notes

- Depends on T3 (error handling complete) and T4 (benchmark utilities for test image generation)
- T6 (integration/e2e tests) depends on this task
- T7 (final verification) depends on this task

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` — version `>=9.0.2,<10` (from `pyproject.toml`)
  - **Fixtures**: `tmp_path` for temporary files, `monkeypatch` for environment variables
  - **Assertion**: `pytest.raises(ExceptionType)` for exception testing
  - **Documentation**: https://docs.pytest.org/en/stable/

- **Mocking strategy**: Mock the LangChain `ChatOpenAI` and tool-calling response (`tool_calls`) to avoid real API calls.
  - Use `monkeypatch` or `unittest.mock.patch` (NOTE: ruff bans `unittest.mock` import. Use `from unittest.mock import patch, MagicMock` — the ruff ban is on `unittest` and `unittest.TestCase`, not `unittest.mock`). **CORRECTION**: Check ruff.toml — `"unittest.mock"` IS banned. Use `pytest`'s `monkeypatch` fixture instead, or import `mock` from `pytest-mock` if available. Since `pytest-mock` is not in `pyproject.toml`, use `monkeypatch` to patch attributes.
  - **Alternative**: Patch at the service module level. For example, patch `nl_processing.extract_text_from_image.service.ChatOpenAI` to return a mock that returns `ExtractedText(text="expected text")`.

## Implementation steps (developer-facing)

1. **Create `tests/unit/extract_text_from_image/test_image_encoding.py`** — tests for `image_encoding.py`:
   - **Test `get_image_format`**: Verify `.png`, `.jpg`, `.JPEG` (uppercase), `.gif`, `.webp` → correct lowercase extension
   - **Test `encode_path_to_base64`**: Create a small PNG file using `generate_test_image()` in `tmp_path`, encode it, verify the result is a non-empty base64 string and media type is `image/png`
   - **Test `encode_cv2_to_base64`**: Create a numpy array (small white image), encode it, verify base64 string and `image/png` media type
   - **Test `validate_image_format` — valid formats**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` → no exception
   - **Test `validate_image_format` — invalid formats**: `.bmp`, `.tiff`, `.svg`, `""` (no extension) → `UnsupportedImageFormatError`
   - **Test `validate_image_format` — case insensitive**: `.PNG`, `.JPG` → no exception (extension is lowered)

2. **Create `tests/unit/extract_text_from_image/test_error_handling.py`** — tests for error paths:
   - **Test format validation in `extract_from_path`**: Call `extractor.extract_from_path("test.bmp")` → `UnsupportedImageFormatError` raised, no API call (mock the chain to verify it was NOT called)
   - **Test TargetLanguageNotFoundError**: Mock chain to return `ExtractedText(text="")` → `TargetLanguageNotFoundError` raised
   - **Test TargetLanguageNotFoundError for whitespace**: Mock chain to return `ExtractedText(text="   \n  ")` → `TargetLanguageNotFoundError` raised
   - **Test APIError wrapping**: Mock chain to raise `RuntimeError("API failed")` → `APIError` raised with `__cause__` being the original `RuntimeError`
   - **Test no raw exception leak**: Mock chain to raise various exceptions → all wrapped as `APIError`

3. **Create `tests/unit/extract_text_from_image/test_extract_text_from_image.py`** — tests for the main service:
   - **Test constructor defaults**: `ImageTextExtractor()` defaults to `Language.NL` and `model="gpt-5-nano"` (GPT-5 Mini is the evaluation baseline)
   - **Test `extract_from_path` happy path**: Mock chain to return `ExtractedText(text="De kat zit op de mat")`, create a test PNG in `tmp_path`, call `extract_from_path()`, verify the returned text matches
   - **Test `extract_from_cv2` happy path**: Mock chain to return `ExtractedText(text="Hallo wereld")`, create a numpy array, call `extract_from_cv2()`, verify the returned text matches
   - **Test both methods converge**: Verify that both `extract_from_path` and `extract_from_cv2` invoke the same internal `_extract` method (can verify by checking mock call patterns)

   **Mocking approach** (using `monkeypatch`):
   - Patch `ImageTextExtractor.__init__` to set `self._llm` to a mock object that returns a predefined `ExtractedText` when `.invoke()` is called.
   - Or patch `ChatOpenAI` at import time to return a mock.
   - The key is: no real API call, no real `OPENAI_API_KEY` needed.
   - Since the constructor calls `os.environ["OPENAI_API_KEY"]`, use `monkeypatch.setenv("OPENAI_API_KEY", "test-key")` in the test fixture.
   - Since the constructor calls `load_prompt()`, either create a real prompt JSON fixture in `tmp_path` or patch `load_prompt` to return a mock `ChatPromptTemplate`.

4. **Run all unit tests**: `uv run pytest tests/unit/extract_text_from_image/ -x -v`

5. **Run linting**: `uv run ruff format tests/unit/extract_text_from_image/ && uv run ruff check tests/unit/extract_text_from_image/`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Tests use `tmp_path` for temporary files. Mock API key via `monkeypatch.setenv`. No real API calls. No production resources accessed.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses pytest fixtures (`tmp_path`, `monkeypatch`) — no custom test infrastructure.
- **Correct libraries only**: `pytest` from `pyproject.toml`.
- **Correct file locations**: Tests in `tests/unit/extract_text_from_image/` per architecture.
- **No regressions**: New test files — no existing tests affected (old broken test was deleted in T1).

## Error handling + correctness rules (mandatory)

- Tests must not silently pass — use explicit assertions.
- Tests must not catch exceptions broadly — use `pytest.raises()` for expected exceptions.
- Every error path in the code must have a corresponding test.

## Zero legacy tolerance rule (mandatory)

- No legacy tests to remove — old broken test was already deleted in T1.
- New tests cover all current functionality.

## Acceptance criteria (testable)

1. `uv run pytest tests/unit/extract_text_from_image/ -x -v` passes (all tests green)
2. Tests cover: image encoding (path, cv2), format validation (valid and invalid), error handling (all 3 exception types), happy-path extraction (mocked)
3. No real API calls are made during unit tests (no `OPENAI_API_KEY` required)
4. `uv run ruff check tests/unit/extract_text_from_image/` passes
5. All test files are under 200 lines
6. At least these test functions exist:
   - Format validation: valid formats pass, invalid formats raise `UnsupportedImageFormatError`
   - Empty text → `TargetLanguageNotFoundError`
   - API error → `APIError` with `__cause__`
   - Happy path → correct text returned

## Verification / quality gates

- [ ] Unit tests added in `tests/unit/extract_text_from_image/`
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist for all 3 exception types
- [ ] No real API calls in unit tests

## Edge cases

- Mocking `OPENAI_API_KEY` — must be set before `ImageTextExtractor` is constructed. Use `monkeypatch.setenv` in a fixture.
- Mocking `load_prompt` — the constructor loads the prompt from the filesystem. Either provide a real prompt fixture or patch the function.
- `cv2.imencode` failure — create a test with an invalid numpy array if possible. This is a rare edge case.
- File not found — `extract_from_path("nonexistent.png")` should raise `FileNotFoundError` (from file reading, after format validation passes). Test this.

## Rollout / rollback (if relevant)

- Rollout: Create test files in a single commit.
- Rollback: Delete the test files.

## Notes / risks

- **Risk**: Mocking LangChain internals may be fragile if the internal API changes. **Mitigation**: Mock at the highest possible level (the `_llm.invoke()` call). Keep mocking simple.
- **Risk**: `ruff` bans `unittest.mock`. **Mitigation**: Use `monkeypatch` from pytest for attribute patching and environment variables. For complex mocking (return values, call tracking), consider adding `pytest-mock` to dev dependencies — but check first if `monkeypatch` is sufficient. If `monkeypatch` is insufficient, propose adding `pytest-mock` and document the change.
