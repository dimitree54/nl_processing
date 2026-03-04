---
Task ID: `T3`
Title: `Create unit tests for WordExtractor with mocked LangChain chain`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `done`
---

## Goal / value

Unit tests exist that validate `WordExtractor` logic with a mocked LangChain chain: constructor behavior, happy-path extraction, empty-list for non-target language, and `APIError` wrapping. Tests run without any API calls.

## Context (contract mapping)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR1-FR11
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Test Strategy" (unit tests section)
- Reference tests: `tests/unit/extract_text_from_image/conftest.py`, `test_extract_text_from_image.py`, `test_error_handling.py`

## Preconditions

- T2 completed: `WordExtractor` class exists in `service.py`
- `tests/unit/extract_words_from_text/__init__.py` already exists (empty)

## Non-goals

- Real API calls (that's T4)
- Quality validation of prompt (that's T4)
- E2e scenarios (that's T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/unit/extract_words_from_text/conftest.py` -- create
- `tests/unit/extract_words_from_text/test_word_extractor.py` -- create
- `tests/unit/extract_words_from_text/test_error_handling.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- any module source code
- `tests/unit/extract_text_from_image/` -- other module tests
- `tests/unit/core/` -- other module tests
- `tests/integration/`, `tests/e2e/` -- other test levels

**Test scope:**
- Tests go in: `tests/unit/extract_words_from_text/`
- Test command: `uv run pytest tests/unit/extract_words_from_text/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/unit/extract_words_from_text/conftest.py` -- async chain mock helpers
- `tests/unit/extract_words_from_text/test_word_extractor.py` -- constructor and happy-path tests
- `tests/unit/extract_words_from_text/test_error_handling.py` -- error handling tests

## Dependencies and sequencing notes

- Depends on T2 for the `WordExtractor` class to test against.
- Should run before T4/T5 to catch basic logic errors early.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2, per `pyproject.toml`)
  - **`pytest.mark.asyncio`**: Required for testing async methods. `pytest-asyncio` (>=1.3.0) is installed.
  - **`monkeypatch`**: Used to set `OPENAI_API_KEY` env var for constructor tests.
- **Pattern**: Follow the exact mock pattern from `tests/unit/extract_text_from_image/conftest.py`:
  - `_AsyncChainMock` class with `ainvoke_calls` tracking
  - `_AsyncChainMockError` class for error path testing
  - `make_tool_response()` helper to build fake `tool_calls` responses

## Implementation steps (developer-facing)

1. **Create `conftest.py`** in `tests/unit/extract_words_from_text/` following the reference pattern from `tests/unit/extract_text_from_image/conftest.py`:

   ```python
   from types import SimpleNamespace

   class _AsyncChainMock:
       def __init__(self, return_value: SimpleNamespace) -> None:
           self.ainvoke_calls: list[dict[str, list[object]]] = []
           self._return_value = return_value

       async def ainvoke(self, input_dict: dict[str, list[object]]) -> SimpleNamespace:
           self.ainvoke_calls.append(input_dict)
           return self._return_value

   class _AsyncChainMockError:
       def __init__(self, exception: Exception) -> None:
           self._exception = exception

       async def ainvoke(self, _input_dict: dict[str, list[object]]) -> SimpleNamespace:
           raise self._exception

   def make_tool_response(words: list[dict[str, str]]) -> SimpleNamespace:
       resp = SimpleNamespace()
       resp.tool_calls = [{"args": {"words": words}}]
       return resp
   ```

   Note: The `make_tool_response` differs from the reference -- it takes a list of word dicts (matching `_WordList.words` field) instead of a text string.

2. **Create `test_word_extractor.py`** with these test cases:

   a. `test_constructor_defaults` -- verify default `language=Language.NL`, chain is created
   b. `test_constructor_custom_params` -- verify custom language and model
   c. `test_constructor_missing_prompt_file` -- verify `FileNotFoundError` for unsupported language (e.g., `Language.RU`)
   d. `test_extract_happy_path` -- mock chain returns word entries, verify correct `list[WordEntry]` returned
   e. `test_extract_returns_word_entry_objects` -- verify each item is a `WordEntry` with `normalized_form` and `word_type`
   f. `test_extract_empty_list_for_non_target_language` -- mock chain returns empty words list, verify empty list returned
   g. `test_extract_invokes_chain_with_text` -- verify `ainvoke` is called with the correct input structure

3. **Create `test_error_handling.py`** with these test cases:

   a. `test_api_error_wrapping_runtime_error` -- RuntimeError from chain wrapped as APIError
   b. `test_api_error_wrapping_various_exceptions` -- ValueError, ConnectionError, KeyError, generic Exception all wrapped as APIError
   c. `test_api_error_preserves_cause` -- verify `__cause__` is preserved

4. **All async test methods** must be decorated with `@pytest.mark.asyncio`.

5. **All tests use `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`** before constructing `WordExtractor`.

6. **Mock pattern**: Construct `WordExtractor()`, then replace `extractor._chain` with the mock before calling `extract()`.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: N/A -- tests use mocked chain, no real API calls.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the exact test patterns from `tests/unit/extract_text_from_image/`.
- **No regressions**: New test files only.
- **Correct file locations**: `tests/unit/extract_words_from_text/`.

## Error handling + correctness rules (mandatory)

- Tests must verify that errors are NOT silenced -- APIError wrapping preserves the original exception as `__cause__`.
- Tests must verify that empty list is returned (not `None`, not an exception) for non-target language.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to remove (existing `__init__.py` is empty and stays).

## Acceptance criteria (testable)

1. `tests/unit/extract_words_from_text/conftest.py` exists with mock helpers
2. `tests/unit/extract_words_from_text/test_word_extractor.py` exists with >= 5 test functions
3. `tests/unit/extract_words_from_text/test_error_handling.py` exists with >= 3 test functions
4. `uv run pytest tests/unit/extract_words_from_text/ -x -v` passes (all tests green)
5. No real API calls are made during unit tests
6. Tests cover: constructor defaults, happy path, empty list, APIError wrapping
7. All test files pass ruff format and check
8. Each test file is under 200 lines

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/extract_words_from_text/ -x -v`
- [ ] Ruff format and check pass on test files
- [ ] Pylint 200-line limit passes on test files
- [ ] No real API calls in unit tests
- [ ] Negative-path tests exist (APIError wrapping, empty list)

## Edge cases

- Mock response must match the wrapper model structure (`{"words": [...]}`) not the `WordEntry` structure directly
- `monkeypatch.setenv` must be called before `WordExtractor()` construction (constructor creates `ChatOpenAI` which reads the env var)

## Notes / risks

- **Risk**: Mock response structure doesn't match actual LLM response format.
  - **Mitigation**: Mirror the reference implementation's mock pattern exactly, adjusted for the wrapper model.
