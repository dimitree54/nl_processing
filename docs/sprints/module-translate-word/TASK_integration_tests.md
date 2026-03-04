---
Task ID: `T4`
Title: `Create integration tests with real API calls for translation quality and performance`
Sprint: `2026-03-03_translate-word`
Module: `translate_word`
Depends on: `T2`
Parallelizable: `yes, with T5 and T6`
Owner: `Developer`
Status: `done`
---

## Goal / value

Integration tests validate translation accuracy (10 unambiguous Dutch words with 100% exact match to Russian ground truth) and performance (<1s for 10 words) with real API calls.

## Context (contract mapping)

- Requirements: `nl_processing/translate_word/docs/prd_translate_word.md` -- FR10, FR11, NFR1
- Architecture: `nl_processing/translate_word/docs/architecture_translate_word.md` -- "Test Strategy" (integration tests)
- Epics: `docs/planning-artifacts/epics.md` -- Story 5.2
- Reference: `tests/integration/extract_text_from_image/test_extraction_accuracy.py`

## Preconditions

- T2 completed: `WordTranslator` class is functional
- `OPENAI_API_KEY` configured in Doppler

## Non-goals

- Mocked tests (T3), e2e scenarios (T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/integration/translate_word/__init__.py` -- create (empty)
- `tests/integration/translate_word/test_translation_accuracy.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/`, other module tests, unit/e2e dirs

**Test scope:**
- Tests go in: `tests/integration/translate_word/`
- Test command: `doppler run -- uv run pytest tests/integration/translate_word/ -x -v`

## Touched surface (expected files / modules)

- `tests/integration/translate_word/__init__.py` -- new (empty)
- `tests/integration/translate_word/test_translation_accuracy.py` -- new

## Dependencies and sequencing notes

- Depends on T2. Can run in parallel with T5 and T6.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2), `pytest-asyncio`, `time` (stdlib).

## Implementation steps (developer-facing)

1. **Create `tests/integration/translate_word/`** with empty `__init__.py`.

2. **Create `test_translation_accuracy.py`** with:

   a. **Quality test -- 10 unambiguous Dutch words** (TW-FR10):
      ```python
      test_cases = [
          ("huis", "дом"),
          ("boek", "книга"),
          ("water", "вода"),
          ("zon", "солнце"),
          ("brood", "хлеб"),
          ("melk", "молоко"),
          ("school", "школа"),
          ("tafel", "стол"),
          ("stoel", "стул"),
          ("deur", "дверь"),
      ]
      ```
      - Pass all 10 words as a single batch
      - Verify `len(results) == 10`
      - Verify each `results[i].translation` matches the expected Russian translation exactly
      - Assert 100% exact match (all 10 must pass)

   b. **One-to-one mapping test**:
      - Pass 5 words, verify output has exactly 5 `TranslationResult` objects
      - Verify order is preserved

   c. **Performance test** (TW-FR11, TW-NFR1):
      - Translate 10 words
      - Time with `time.time()`
      - Assert `elapsed < 1` second

   d. **Empty input test**:
      - `translator.translate([])` returns `[]`
      - No API call made (verified by timing: should be near-instant)

3. **All tests** use `@pytest.mark.asyncio` and create their own `WordTranslator` instance.

4. **Cost**: 2-3 API calls per test run. Acceptable per SNFR18.

## Production safety constraints (mandatory)

- N/A.

## Anti-disaster constraints (mandatory)

- Follow reference pattern. Use unambiguous words for exact-match testing.

## Error handling + correctness rules (mandatory)

- Clear assertion messages with expected vs actual translations.
- No `pytest.skip`.

## Zero legacy tolerance rule (mandatory)

- No legacy files.

## Acceptance criteria (testable)

1. `tests/integration/translate_word/__init__.py` exists (empty)
2. `test_translation_accuracy.py` exists with >= 3 test functions
3. `doppler run -- uv run pytest tests/integration/translate_word/ -x -v` passes
4. Quality test: 10 words, 100% exact match
5. Performance test: <1s for 10 words
6. One-to-one mapping verified (`len(output) == len(input)`)
7. Ruff passes, each file under 200 lines

## Verification / quality gates

- [ ] Integration tests pass: `doppler run -- uv run pytest tests/integration/translate_word/ -x -v`
- [ ] Ruff format and check pass
- [ ] Pylint 200-line limit passes

## Edge cases

- Exact-match test words must be truly unambiguous (single clear Russian translation). Avoid words with multiple valid translations.
- Performance test includes network round-trip. The <1s target is tight -- if consistently failing, the model or prompt may need adjustment.

## Notes / risks

- **Risk**: Some Dutch words may have multiple valid Russian translations, causing exact-match failures.
  - **Mitigation**: Carefully curate 10 words with unambiguous translations. Use common, everyday nouns.
- **Risk**: <1s performance may fail due to network latency.
  - **Mitigation**: Single API call for all 10 words (batch). If consistently slow, investigate model or prompt size.
