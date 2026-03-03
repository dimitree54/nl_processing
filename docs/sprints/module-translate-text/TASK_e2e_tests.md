---
Task ID: `T5`
Title: `Create e2e tests for full translation scenarios`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `T2`
Parallelizable: `yes, with T4 and T6`
Owner: `Developer`
Status: `planned`
---

## Goal / value

E2e tests validate full translation scenarios with varied markdown content, testing the module as a black box in realistic usage patterns.

## Context (contract mapping)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md` -- FR1-FR4
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md` -- "Test Strategy" (e2e tests)
- Reference: `tests/e2e/extract_text_from_image/test_full_extraction.py`

## Preconditions

- T2 completed: `TextTranslator` class is functional
- `OPENAI_API_KEY` configured in Doppler

## Non-goals

- Exhaustive quality metrics (T4), unit-level mocking (T3)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/e2e/translate_text/__init__.py` -- create (empty)
- `tests/e2e/translate_text/test_full_translation.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, unit/integration dirs

**Test scope:**
- Tests go in: `tests/e2e/translate_text/`
- Test command: `doppler run -- uv run pytest tests/e2e/translate_text/ -x -v`

## Touched surface (expected files / modules)

- `tests/e2e/translate_text/__init__.py` -- new (empty)
- `tests/e2e/translate_text/test_full_translation.py` -- new

## Dependencies and sequencing notes

- Depends on T2. Can run in parallel with T4 and T6.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio` (>=1.3.0).

## Implementation steps (developer-facing)

1. **Create `tests/e2e/translate_text/`** with empty `__init__.py`.

2. **Create `test_full_translation.py`** with:

   a. **Full translation pipeline** -- translate a multi-paragraph Dutch markdown text. Verify output is a non-empty string.

   b. **Empty input handling** -- verify `translate("")` returns `""`.

   c. **Markdown-heavy input** -- translate Dutch text with multiple headings, nested lists, bold+italic. Verify output contains markdown symbols.

   d. **Short sentence translation** -- translate a simple Dutch sentence. Verify output is non-empty and is a string.

   e. **Unsupported pair raises at init** -- verify `TextTranslator(source_language=Language.RU, target_language=Language.NL)` raises `ValueError`.

3. **E2e tests focus on** structural correctness (non-empty output, correct types, markdown present) rather than exact translation quality.

4. **All tests** use `@pytest.mark.asyncio`.

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Follow reference from `tests/e2e/extract_text_from_image/test_full_extraction.py`.

## Error handling + correctness rules (mandatory)

- Clear assertion messages. No `pytest.skip`.

## Zero legacy tolerance rule (mandatory)

- No legacy files.

## Acceptance criteria (testable)

1. `tests/e2e/translate_text/__init__.py` exists (empty)
2. `test_full_translation.py` exists with >= 4 test functions
3. `doppler run -- uv run pytest tests/e2e/translate_text/ -x -v` passes
4. Tests cover: full translation, empty input, markdown, unsupported pair
5. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] E2e tests pass: `doppler run -- uv run pytest tests/e2e/translate_text/ -x -v`
- [ ] Ruff format and check pass

## Edge cases

- Init-time validation test should not use `@pytest.mark.asyncio` (it tests synchronous init behavior).

## Notes / risks

- **Risk**: E2e tests may be brittle due to LLM variability.
  - **Mitigation**: Focus on structural assertions, not exact content.
