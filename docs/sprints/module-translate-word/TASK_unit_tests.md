---
Task ID: `T3`
Title: `Create unit tests for WordTranslator with mocked chain`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `T2`
Parallelizable: `no`
Owner: `Developer`
Status: `done`
---

## Goal / value

Unit tests validate `WordTranslator` logic with a mocked chain: constructor behavior (language pair validation), happy-path batch translation, one-to-one mapping enforcement, empty-list handling, and `APIError` wrapping. No API calls.

## Context (contract mapping)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR1-FR4, FR9
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "Test Strategy" (unit tests)
- Reference: `tests/unit/extract_text_from_image/`

## Preconditions

- T2 completed: `WordTranslator` class exists
- `tests/unit/translate_word/__init__.py` already exists (empty)

## Non-goals

- Real API calls (T4), e2e scenarios (T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/unit/translate_word/conftest.py` -- create
- `tests/unit/translate_word/test_word_translator.py` -- create
- `tests/unit/translate_word/test_error_handling.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, integration/e2e dirs

**Test scope:**
- Tests go in: `tests/unit/translate_word/`
- Test command: `uv run pytest tests/unit/translate_word/ -x -v`

## Touched surface (expected files / modules)

- `tests/unit/translate_word/conftest.py` -- async chain mock helpers
- `tests/unit/translate_word/test_word_translator.py` -- constructor and happy-path tests
- `tests/unit/translate_word/test_error_handling.py` -- error handling tests

## Dependencies and sequencing notes

- Depends on T2 for `WordTranslator` class.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio` (>=1.3.0).

## Implementation steps (developer-facing)

1. **Create `conftest.py`** with mock helpers:
   - `_AsyncChainMock` with `ainvoke_calls` tracking
   - `_AsyncChainMockError` for error path
   - `make_tool_response(translations: list[dict[str, str]])` -- returns `SimpleNamespace(tool_calls=[{"args": {"translations": translations}}])`

2. **Create `test_word_translator.py`** with:
   a. `test_constructor_valid_pair` -- NL->RU succeeds
   b. `test_constructor_unsupported_pair` -- RU->NL raises `ValueError`
   c. `test_constructor_custom_model` -- custom model accepted
   d. `test_translate_happy_path` -- mock returns 3 translations for 3 words, verify correct `list[TranslationResult]`
   e. `test_translate_one_to_one_mapping` -- verify `len(output) == len(input)` with mock
   f. `test_translate_empty_input` -- empty list returns empty list (no chain call)
   g. `test_translate_preserves_order` -- verify translations match input word order
   h. `test_translate_returns_translation_result_objects` -- verify each item is `TranslationResult` with `translation` field

3. **Create `test_error_handling.py`** with:
   a. `test_api_error_wrapping` -- RuntimeError wrapped as APIError
   b. `test_api_error_various_exceptions` -- multiple types wrapped
   c. `test_api_error_preserves_cause` -- `__cause__` preserved

4. **All async tests** use `@pytest.mark.asyncio`.

5. **Constructor tests** use `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`.

6. **Empty input test** should verify zero chain invocations.

## Production safety constraints (mandatory)

- N/A -- mocked tests.

## Anti-disaster constraints (mandatory)

- Follow reference test patterns.

## Error handling + correctness rules (mandatory)

- Tests verify errors are NOT silenced.
- Tests verify empty list returned (not None, not exception) for empty input.
- Tests verify one-to-one mapping semantics.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to remove.

## Acceptance criteria (testable)

1. `conftest.py`, `test_word_translator.py`, `test_error_handling.py` exist
2. `uv run pytest tests/unit/translate_word/ -x -v` passes
3. Tests cover: valid/invalid constructor, empty input, happy path, one-to-one mapping, APIError
4. No real API calls
5. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] Unit tests pass: `uv run pytest tests/unit/translate_word/ -x -v`
- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes
- [ ] Negative-path tests exist

## Edge cases

- Mock response must use `{"translations": [...]}` structure matching `_TranslationBatch`
- Empty input test must verify zero `ainvoke_calls`

## Notes / risks

- Same patterns as other sprints' T3, adjusted for `WordTranslator` specifics.
