---
Task ID: `T4`
Title: `Create integration tests with real API calls and quality validation`
Sprint: `2026-03-03_extract-words-from-text`
Module: `extract_words_from_text`
Depends on: `T2`
Parallelizable: `yes, with T5 and T6`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Integration tests exist that make real OpenAI API calls to validate extraction accuracy (5 curated test cases with 100% set-based match) and performance (<5s for ~100 words). These tests are the primary quality gate for prompt quality.

## Context (contract mapping)

- Requirements: `nl_processing/extract_words_from_text/docs/prd_extract_words_from_text.md` -- FR12-FR14, NFR1
- Architecture: `nl_processing/extract_words_from_text/docs/architecture_extract_words_from_text.md` -- "Test Strategy" (integration tests), "Set-Based Test Validation"
- Reference tests: `tests/integration/extract_text_from_image/test_extraction_accuracy.py`
- Epics: `docs/planning-artifacts/epics.md` -- Story 3.2

## Preconditions

- T2 completed: `WordExtractor` class is functional
- `OPENAI_API_KEY` is configured in Doppler
- `tests/integration/extract_words_from_text/` directory needs to be created (with `__init__.py`)

## Non-goals

- Mocked tests (that's T3)
- Full pipeline scenarios (that's T5)
- Prompt tuning beyond making tests pass

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED -- this task may ONLY touch:**
- `tests/integration/extract_words_from_text/__init__.py` -- create (empty)
- `tests/integration/extract_words_from_text/test_extraction_accuracy.py` -- create

**FORBIDDEN -- this task must NEVER touch:**
- `nl_processing/` -- any module source code (unless prompt needs iteration, which stays in T1's files)
- `tests/integration/extract_text_from_image/` -- other module tests
- `tests/unit/`, `tests/e2e/` -- other test levels

**Test scope:**
- Tests go in: `tests/integration/extract_words_from_text/`
- Test command: `doppler run -- uv run pytest tests/integration/extract_words_from_text/ -x -v`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

- `tests/integration/extract_words_from_text/__init__.py` -- new (empty)
- `tests/integration/extract_words_from_text/test_extraction_accuracy.py` -- new

## Dependencies and sequencing notes

- Depends on T2 for the working `WordExtractor` class.
- Can run in parallel with T5 (e2e tests) and T6 (vulture cleanup).
- If tests fail, may require prompt iteration (going back to T1's prompt file) -- but this is normal development flow, not a task dependency.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pytest` (>=9.0.2)
  - **`pytest.mark.asyncio`**: For async test methods.
  - **`time` module**: For performance benchmarking (wall clock time).
- **API**: OpenAI API (via LangChain)
  - **Rate limits**: Standard OpenAI rate limits apply. Tests should be designed to minimize API calls.
  - **Cost awareness**: Each test case = 1 API call. 5 quality tests + 1 performance test = 6 API calls per run.

## Implementation steps (developer-facing)

1. **Create `tests/integration/extract_words_from_text/` directory** with empty `__init__.py`.

2. **Create `test_extraction_accuracy.py`** with these test cases:

   a. **5 curated quality test cases** (EWT-FR12, EWT-FR14). Each test:
      - Defines a 1-2 sentence Dutch input text
      - Defines the expected set of `(normalized_form, word_type)` tuples
      - Calls `await extractor.extract(text)`
      - Compares output as sets: `{(w.normalized_form, w.word_type) for w in result} == expected_set`
      - Each test covers diverse word types

   b. **Suggested test cases** (linguistically accurate Dutch):

      - **Test 1** (nouns + verbs): `"De grote kat loopt door de tuin."` -- expects de kat (noun), groot (adjective), lopen (verb), de tuin (noun), door (preposition)
      - **Test 2** (proper nouns + prepositions): `"Jan woont in Nederland."` -- expects Jan (proper_noun_person), wonen (verb), in (preposition), Nederland (proper_noun_country)
      - **Test 3** (articles de/het + adjectives): `"Het kleine kind speelt met de rode bal."` -- expects het kind (noun), klein (adjective), spelen (verb), met (preposition), de bal (noun), rood (adjective)
      - **Test 4** (compound expression): `"Zij gaat er vandoor met haar vriend."` -- expects er vandoor gaan (compound verb or similar), zij (pronoun), met (preposition), haar (pronoun/possessive), de vriend (noun)
      - **Test 5** (non-Dutch returns empty): `"The quick brown fox jumps over the lazy dog."` -- expects empty set

   c. **Performance test** (EWT-FR13, EWT-NFR1):
      - Create a ~100-word Dutch text
      - Time the extraction: `start = time.time()` ... `elapsed = time.time() - start`
      - Assert `elapsed < 5` seconds

3. **Set-based comparison pattern** (EWT architecture decision):
   ```python
   result = await extractor.extract(dutch_text)
   actual = {(w.normalized_form, w.word_type) for w in result}
   assert actual == expected_set, f"Mismatch.\nExpected: {expected_set}\nGot: {actual}"
   ```

4. **Each test creates its own `WordExtractor()` instance** with default params.

5. **All tests use `@pytest.mark.asyncio`** decorator.

## Production safety constraints (mandatory)

- **Database operations**: N/A.
- **Resource isolation**: Tests use the OpenAI API via Doppler-managed keys. No local resources shared with production.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow the integration test pattern from `tests/integration/extract_text_from_image/test_extraction_accuracy.py`.
- **Correct file locations**: `tests/integration/extract_words_from_text/`.
- **No regressions**: New test files only.

## Error handling + correctness rules (mandatory)

- Tests must produce clear error messages on failure (include expected vs actual sets in assertion messages).
- No `pytest.skip` or `pytest.mark.skip` allowed.

## Zero legacy tolerance rule (mandatory)

- No legacy test files to remove.

## Acceptance criteria (testable)

1. `tests/integration/extract_words_from_text/__init__.py` exists (empty)
2. `tests/integration/extract_words_from_text/test_extraction_accuracy.py` exists with >= 6 test functions (5 quality + 1 performance)
3. `doppler run -- uv run pytest tests/integration/extract_words_from_text/ -x -v` passes (all tests green)
4. Each quality test uses set-based comparison `(normalized_form, word_type)`
5. Each quality test covers diverse word types (nouns, verbs, adjectives, prepositions, proper nouns)
6. Performance test verifies <5s for ~100 words
7. Non-Dutch text test verifies empty list return
8. All test files pass ruff format and check
9. Each test file is under 200 lines

## Verification / quality gates

- [ ] Integration tests pass: `doppler run -- uv run pytest tests/integration/extract_words_from_text/ -x -v`
- [ ] Ruff format and check pass on test files
- [ ] Pylint 200-line limit passes
- [ ] All 5 quality test cases achieve 100% set-based accuracy
- [ ] Performance test passes (<5s)

## Edge cases

- LLM may produce slightly different word types (e.g., "adjective" vs "bijvoeglijk_naamwoord"). The prompt must be explicit about the expected type names.
- LLM may extract additional words not in the expected set. Consider whether to use `assert actual == expected` (exact) or `assert expected.issubset(actual)` (minimum coverage). Per PRD, use exact set match.
- The performance test may be flaky due to network latency. The 5-second threshold should accommodate typical API response times.

## Notes / risks

- **Risk**: Prompt quality may not achieve 100% accuracy on first attempt.
  - **Mitigation**: Iterate on the prompt (T1's files) based on test failures. This is expected development workflow.
- **Risk**: Test case design may not cover all word types mentioned in the PRD.
  - **Mitigation**: Each test case is explicitly designed to cover specific word types as listed in EWT-FR14.
- **Cost**: 6 API calls per test run. Acceptable per SNFR18.
