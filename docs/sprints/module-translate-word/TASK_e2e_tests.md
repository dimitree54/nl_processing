---
Task ID: `T5`
Title: `Create e2e tests for full word translation scenarios`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `T2`
Parallelizable: `yes, with T4 and T6`
Owner: `Developer`
Status: `done`
---

## Goal / value

E2e tests validate full word translation scenarios with realistic pipeline input, testing the module as a black box in usage patterns that mirror upstream module output (e.g., word lists from `extract_words_from_text`).

## Context (contract mapping)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR2-FR4
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "Test Strategy" (e2e tests)
- Reference: `tests/e2e/extract_text_from_image/test_full_extraction.py`

## Preconditions

- T2 completed: `WordTranslator` class is functional
- `OPENAI_API_KEY` configured in Doppler

## Non-goals

- Exact-match quality validation (T4), unit-level mocking (T3)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/e2e/translate_word/__init__.py` -- create (empty)
- `tests/e2e/translate_word/test_full_translation.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, unit/integration dirs

**Test scope:**
- Tests go in: `tests/e2e/translate_word/`
- Test command: `doppler run -- uv run pytest tests/e2e/translate_word/ -x -v`

## Touched surface (expected files / modules)

- `tests/e2e/translate_word/__init__.py` -- new (empty)
- `tests/e2e/translate_word/test_full_translation.py` -- new

## Dependencies and sequencing notes

- Depends on T2. Can run in parallel with T4 and T6.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio` (>=1.3.0).

## Implementation steps (developer-facing)

1. **Create `tests/e2e/translate_word/`** with empty `__init__.py`.

2. **Create `test_full_translation.py`** with:

   a. **Realistic pipeline input** -- translate a list of normalized Dutch words (like output from `extract_words_from_text`): `["de kat", "lopen", "mooi", "in", "Nederland"]`. Verify output is a list of `TranslationResult` objects with non-empty `translation` fields.

   b. **One-to-one mapping verification** -- pass N words, verify exactly N results in the same order. Each result is a `TranslationResult` with a non-empty `translation`.

   c. **Empty input handling** -- `translate([])` returns `[]`.

   d. **Unsupported pair at init** -- `WordTranslator(source_language=Language.RU, target_language=Language.NL)` raises `ValueError`.

   e. **Single word translation** -- translate `["huis"]`, verify output is a list with 1 `TranslationResult`.

3. **E2e tests focus on structural correctness**: non-empty output, correct types, correct count, order preservation -- not exact translation accuracy.

4. **All async tests** use `@pytest.mark.asyncio`.

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Follow reference pattern.

## Error handling + correctness rules (mandatory)

- Clear assertion messages. No `pytest.skip`.

## Zero legacy tolerance rule (mandatory)

- No legacy files.

## Acceptance criteria (testable)

1. `tests/e2e/translate_word/__init__.py` exists (empty)
2. `test_full_translation.py` exists with >= 4 test functions
3. `doppler run -- uv run pytest tests/e2e/translate_word/ -x -v` passes
4. Tests cover: realistic input, one-to-one mapping, empty input, unsupported pair
5. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] E2e tests pass: `doppler run -- uv run pytest tests/e2e/translate_word/ -x -v`
- [ ] Ruff format and check pass

## Edge cases

- Init-time validation test (unsupported pair) is synchronous, not async.

## Notes / risks

- **Risk**: E2e tests may be brittle if structural assertions are too strict.
  - **Mitigation**: Focus on type and count assertions.
