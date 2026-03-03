---
Task ID: `T3`
Title: `Create unit tests for TextTranslator with mocked chain`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Unit tests validate `TextTranslator` logic with a mocked chain: constructor behavior (defaults, language pair validation), happy-path translation, empty-string handling, non-Dutch input, and `APIError` wrapping. No API calls.

## Context (contract mapping)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md` -- FR5-FR8
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md` -- "Test Strategy" (unit tests)
- Reference: `tests/unit/extract_text_from_image/`

## Preconditions

- T2 completed: `TextTranslator` class exists
- `tests/unit/translate_text/__init__.py` already exists (empty)

## Non-goals

- Real API calls, prompt quality validation, e2e scenarios

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/unit/translate_text/conftest.py` -- create
- `tests/unit/translate_text/test_text_translator.py` -- create
- `tests/unit/translate_text/test_error_handling.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, integration/e2e test dirs

**Test scope:**
- Tests go in: `tests/unit/translate_text/`
- Test command: `uv run pytest tests/unit/translate_text/ -x -v`

## Touched surface (expected files / modules)

- `tests/unit/translate_text/conftest.py` -- async chain mock helpers
- `tests/unit/translate_text/test_text_translator.py` -- constructor and happy-path tests
- `tests/unit/translate_text/test_error_handling.py` -- error handling tests

## Dependencies and sequencing notes

- Depends on T2 for `TextTranslator` class.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio` (>=1.3.0) -- same as other sprints.

## Implementation steps (developer-facing)

1. **Create `conftest.py`** with mock helpers following the reference pattern:
   - `_AsyncChainMock` with `ainvoke_calls` tracking
   - `_AsyncChainMockError` for error path
   - `make_tool_response(text: str)` -- returns `SimpleNamespace(tool_calls=[{"args": {"text": text}}])`

2. **Create `test_text_translator.py`** with:
   a. `test_constructor_valid_pair` -- NL->RU succeeds
   b. `test_constructor_unsupported_pair` -- RU->NL raises `ValueError`
   c. `test_constructor_custom_model` -- custom model parameter accepted
   d. `test_translate_happy_path` -- mock returns translated text, verify string returned
   e. `test_translate_empty_input` -- empty string returns empty string (no chain call)
   f. `test_translate_whitespace_input` -- whitespace-only returns empty string (no chain call)
   g. `test_translate_invokes_chain` -- verify `ainvoke` called with correct structure

3. **Create `test_error_handling.py`** with:
   a. `test_api_error_wrapping` -- RuntimeError wrapped as APIError
   b. `test_api_error_various_exceptions` -- multiple exception types wrapped
   c. `test_api_error_preserves_cause` -- `__cause__` preserved

4. **All async tests** use `@pytest.mark.asyncio`.

5. **Constructor tests** use `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`.

6. **Empty input tests** should verify the chain mock's `ainvoke_calls` list is empty (no API call made).

## Production safety constraints (mandatory)

- N/A -- mocked tests, no real API calls.

## Anti-disaster constraints (mandatory)

- Follow the reference test patterns from `tests/unit/extract_text_from_image/`.

## Error handling + correctness rules (mandatory)

- Tests verify errors are NOT silenced (APIError wrapping preserves cause).
- Tests verify empty string returned (not None, not exception) for empty input.
- Tests verify ValueError raised at init for invalid pairs.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to remove.

## Acceptance criteria (testable)

1. `conftest.py`, `test_text_translator.py`, `test_error_handling.py` exist
2. `uv run pytest tests/unit/translate_text/ -x -v` passes
3. Tests cover: valid constructor, invalid pair, empty input, happy path, APIError wrapping
4. No real API calls
5. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/translate_text/ -x -v`
- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Negative-path tests exist

## Edge cases

- `test_translate_empty_input` must verify zero chain invocations (the optimization of skipping API calls for empty input)
- Language pair validation test should test both swap directions (NL->RU valid, RU->NL invalid)

## Notes / risks

- **Risk**: Mock structure mismatch with actual response.
  - **Mitigation**: Mirror reference mock pattern, adjusted for `_TranslatedText` wrapper.
