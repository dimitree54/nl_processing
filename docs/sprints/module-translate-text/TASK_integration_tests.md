---
Task ID: `T4`
Title: `Create integration tests with real API calls for translation quality`
Sprint: `2026-03-03_translate-text`
Module: `translate_text`
Depends on: `T2`
Parallelizable: `yes, with T5 and T6`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Integration tests validate translation quality with real API calls: output cleanliness (no LLM chatter), Cyrillic-only output for test without proper nouns, markdown structure preservation, and performance (<5s for ~100 words).

## Context (contract mapping)

- Requirements: `nl_processing/translate_text/docs/prd_translate_text.md` -- FR2-FR4, NFR1, Success Criteria table
- Architecture: `nl_processing/translate_text/docs/architecture_translate_text.md` -- "Test Strategy" (integration tests)
- Epics: `docs/planning-artifacts/epics.md` -- Story 4.2
- Reference: `tests/integration/extract_text_from_image/test_extraction_accuracy.py`

## Preconditions

- T2 completed: `TextTranslator` class is functional
- `OPENAI_API_KEY` configured in Doppler

## Non-goals

- Mocked tests (T3), e2e scenarios (T5), prompt tuning beyond passing tests

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/integration/translate_text/__init__.py` -- create (empty)
- `tests/integration/translate_text/test_translation_quality.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, unit/e2e dirs

**Test scope:**
- Tests go in: `tests/integration/translate_text/`
- Test command: `doppler run -- uv run pytest tests/integration/translate_text/ -x -v`

## Touched surface (expected files / modules)

- `tests/integration/translate_text/__init__.py` -- new (empty)
- `tests/integration/translate_text/test_translation_quality.py` -- new

## Dependencies and sequencing notes

- Depends on T2. Can run in parallel with T5 and T6.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio`, `re` (stdlib), `time` (stdlib).
- **Cyrillic regex**: `re.fullmatch(r"[\u0400-\u04FF\s\p{P}\d#*_\-\n>]+", text)` -- or simpler: check no Latin characters present for the test case without proper nouns.

## Implementation steps (developer-facing)

1. **Create `tests/integration/translate_text/`** with empty `__init__.py`.

2. **Create `test_translation_quality.py`** with these tests:

   a. **Output cleanliness test** (TT-FR4): Translate a short Dutch text. Verify the output does not start with common LLM prefixes like "Here is", "Translation:", "Sure,". The structured output via tool calling should enforce this automatically.

   b. **Cyrillic-only output test** (Success Criteria): Translate a curated Dutch text that contains NO proper nouns (no names, no places). Verify the Russian output contains only Cyrillic characters, punctuation, whitespace, digits, and markdown symbols. Use regex:
      ```python
      import re
      # Allow Cyrillic, whitespace, punctuation, digits, markdown symbols
      assert not re.search(r"[a-zA-Z]", result), f"Latin characters found in: {result}"
      ```

   c. **Markdown structure preservation test** (TT-FR2): Translate a Dutch text with headings (`#`), bold (`**`), italic (`*`), and lists (`-`). Verify the output contains the same markdown structural elements:
      ```python
      assert result.startswith("#")  # heading preserved
      assert "**" in result  # bold preserved
      assert "- " in result  # list items preserved
      ```

   d. **Performance test** (TT-NFR1): Translate ~100-word Dutch text. Assert completion in <5 seconds wall clock time.

   e. **Non-Dutch text returns empty string** (TT-FR8): Translate English-only text. Verify empty string returned.

3. **All tests** use `@pytest.mark.asyncio` and create their own `TextTranslator` instance.

4. **Cost**: ~5 API calls per test run. Acceptable per SNFR18.

## Production safety constraints (mandatory)

- N/A -- OpenAI API via Doppler.

## Anti-disaster constraints (mandatory)

- Follow reference pattern from `tests/integration/extract_text_from_image/`.

## Error handling + correctness rules (mandatory)

- Clear assertion messages showing expected vs actual.
- No `pytest.skip` allowed.

## Zero legacy tolerance rule (mandatory)

- No legacy files.

## Acceptance criteria (testable)

1. `tests/integration/translate_text/__init__.py` exists (empty)
2. `test_translation_quality.py` exists with >= 5 test functions
3. `doppler run -- uv run pytest tests/integration/translate_text/ -x -v` passes
4. Cyrillic-only test passes (no Latin chars in output)
5. Markdown preservation test passes
6. Performance test passes (<5s)
7. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] Integration tests pass: `doppler run -- uv run pytest tests/integration/translate_text/ -x -v`
- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes

## Edge cases

- Cyrillic check must exclude test cases with proper nouns (which may contain Latin characters in the source)
- Markdown test should be structural (presence of symbols) not content-based (exact translation)

## Notes / risks

- **Risk**: LLM may occasionally include Latin characters in output.
  - **Mitigation**: Use structured output enforcement (tool calling). Design test input to have no proper nouns.
