---
Task ID: `T5`
Title: `Create e2e tests for full extraction scenarios`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `T2`
Parallelizable: `yes, with T4 and T6`
Owner: `Developer`
Status: `done`
---

## Goal / value

E2e tests exist that validate full word extraction scenarios with diverse markdown content, covering real-world usage patterns. These tests complement integration tests (T4) by testing broader scenarios and markdown handling.

## Context (contract mapping)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR1, FR4, FR5
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Test Strategy" (e2e tests)
- Reference tests: `tests/e2e/extract_text_from_image/test_full_extraction.py`

## Preconditions

- T2 completed: `WordExtractor` class is functional
- Integration tests (T4) passing is a good sign, but T5 can run in parallel
- `OPENAI_API_KEY` configured in Doppler

## Non-goals

- Exhaustive quality validation (that's T4 with curated test cases)
- Unit-level mocking (that's T3)
- Performance benchmarking (that's T4)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/e2e/extract_words_from_text/__init__.py` -- create (empty)
- `tests/e2e/extract_words_from_text/test_full_extraction.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- any module source code
- `tests/e2e/extract_text_from_image/` -- other module tests
- `tests/unit/`, `tests/integration/` -- other test levels

**Test scope:**
- Tests go in: `tests/e2e/extract_words_from_text/`
- Test command: `doppler run -- uv run pytest tests/e2e/extract_words_from_text/ -x -v`

## Touched surface (expected files / modules)

- `tests/e2e/extract_words_from_text/__init__.py` -- new (empty)
- `tests/e2e/extract_words_from_text/test_full_extraction.py` -- new

## Dependencies and sequencing notes

- Depends on T2 for the working service class.
- Can run in parallel with T4 and T6.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2) + `pytest-asyncio` (>=1.3.0) -- same as T3/T4.

## Implementation steps (developer-facing)

1. **Create `tests/e2e/extract_words_from_text/` directory** with empty `__init__.py`.

2. **Create `test_full_extraction.py`** with these test scenarios:

   a. **Markdown-formatted Dutch text** (EWT-FR4): Test with a text containing markdown headings, bold, italic, lists. Verify that markdown formatting is ignored and only linguistic content is extracted.
      ```python
      text = "# Welkom\n\nDit is een **belangrijke** tekst.\n\n- De kat\n- Het huis"
      result = await extractor.extract(text)
      assert len(result) > 0
      assert all(isinstance(w, WordEntry) for w in result)
      # Verify no markdown symbols in normalized_form
      for w in result:
          assert "#" not in w.normalized_form
          assert "**" not in w.normalized_form
          assert "-" not in w.normalized_form or " " in w.normalized_form  # compound phrases ok
      ```

   b. **Full pipeline scenario** -- longer Dutch text with various word types. Verify the output is a non-empty list of `WordEntry` objects with valid `normalized_form` and `word_type` fields.

   c. **Non-Dutch text returns empty list** (EWT-FR3): Pass English or Russian text, verify empty list.

   d. **Mixed markdown with compound expressions** (EWT-FR5): Text containing phrasal verbs or idiomatic expressions. Verify they appear as single `WordEntry` items.

   e. **Type check on all results**: Every returned item is a `WordEntry` with non-empty `normalized_form` and `word_type`.

3. **E2e tests are less strict** than integration tests on exact accuracy -- focus on:
   - Output structure correctness (valid `WordEntry` objects)
   - Markdown transparency (no formatting artifacts)
   - Empty list for non-target language
   - Non-zero results for valid Dutch input

4. **All tests use `@pytest.mark.asyncio`** decorator.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: Tests use OpenAI API via Doppler-managed keys.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the e2e test pattern from `tests/e2e/extract_text_from_image/test_full_extraction.py`.
- **Correct file locations**: `tests/e2e/extract_words_from_text/`.

## Error handling + correctness rules (mandatory)

- Tests must produce clear assertion messages.
- No `pytest.skip` allowed.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to remove.

## Acceptance criteria (testable)

1. `tests/e2e/extract_words_from_text/__init__.py` exists (empty)
2. `tests/e2e/extract_words_from_text/test_full_extraction.py` exists with >= 4 test functions
3. `doppler run -- uv run pytest tests/e2e/extract_words_from_text/ -x -v` passes
4. Tests cover: markdown transparency, non-Dutch empty list, valid WordEntry output, compound expressions
5. All test files pass ruff format and check
6. Each test file is under 200 lines

## Verification / quality gates

- [ ] E2e tests pass: `doppler run -- uv run pytest tests/e2e/extract_words_from_text/ -x -v`
- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes

## Edge cases

- LLM may occasionally include markdown artifacts in word extraction. The prompt (from T1) must handle this. If e2e tests reveal issues, iterate on the prompt.
- Compound expressions may or may not be detected depending on prompt quality.

## Notes / risks

- **Risk**: E2e tests may be more brittle than integration tests due to broader scenarios.
  - **Mitigation**: Keep assertions focused on structure and type correctness rather than exact word matches.
