---
Task ID: T6
Title: Integration tests — live API translation from synthetic images
Sprint: `translate_text_from_image`
Module: `translate_text_from_image`
Depends on: T4, T5
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Validate the `ImageTextTranslator` service against the live OpenAI API using synthetic test images. These tests cover simple translation, multiline structure, mixed-language filtering, English-only error, and latency gate — the core integration quality bar before moving to e2e with real photos.

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — QA-1 through QA-3, NFR-1, SEED-1 through SEED-4
- Integration test pattern: `packages/extract_text_from_image/tests/integration/.../test_extraction_accuracy.py`
- Translation quality pattern: `packages/translate_text/tests/integration/.../test_translation_quality.py`

## Preconditions

- T4 completed (`ImageTextTranslator` service is implemented).
- T5 completed (`nl_ru.json` prompt asset exists and is loadable).
- `OPENAI_API_KEY` available via doppler (integration tests run with `doppler run --`).

## Non-goals

- E2e tests with real photos (T7).
- Unit tests (T4).
- Prompt quality tuning (done iteratively if tests fail).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_translation_accuracy.py` — NEW
- `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_contract.py` — NEW

**FORBIDDEN — this task must NEVER touch:**
- Any other package's code or tests
- Service source code (fix prompt if tests fail, not the service)

**Test scope:**
- Tests go in: `packages/translate_text_from_image/tests/integration/`
- Test command: `cd packages/translate_text_from_image && doppler run -- env PYTHONPATH=src:../core/src uv run pytest tests/integration -x -v`

## Touched surface (expected files / modules)

- `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_translation_accuracy.py` (new)
- `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_contract.py` (new)

## Dependencies and sequencing notes

- Depends on T4 (service) and T5 (prompt asset).
- T7 depends on this (e2e tests come after integration passes).

## Implementation steps

### Step 1: Create `test_translation_accuracy.py`

Create `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_translation_accuracy.py` (~110-130 lines).

Tests to implement (all `@pytest.mark.asyncio`):

1. **`test_simple_dutch_sentence_translation`** — Generate a synthetic image with "Het regent vandaag in Utrecht". Translate. Assert output contains Cyrillic characters and no Latin characters (excluding proper nouns). Assert non-empty.

2. **`test_multiline_structure_preservation`** — Generate image with multi-line Dutch text. Translate. Assert output preserves line structure (multiple lines in output).

3. **`test_mixed_dutch_russian_translates_only_dutch`** — Generate image with Dutch + Russian text. Translate. Assert output is the Russian translation of the Dutch part only (not a copy of the Russian text already in the image).

4. **`test_english_only_raises_language_not_found`** — Generate image with English-only text. Assert `TargetLanguageNotFoundError` is raised.

5. **`test_translation_latency_gate`** — Generate simple image. Time the translation. Assert < 10 seconds (NFR-1).

6. **`test_output_cleanliness`** — Translate a simple image. Assert output does NOT start with LLM chatter prefixes ("Here is", "Translation:", "Sure,", etc.).

**Image generation**: Use the local `render_text_image()` from `benchmark.py` (created in T5) to generate synthetic images. Tests use `tmp_path` fixture.

**IMPORTANT jscpd note**: These tests must be structurally distinct from `extract_text_from_image/tests/integration/.../test_extraction_accuracy.py` and `translate_text/tests/integration/.../test_translation_quality.py`. Key differences:
- Different function names and assertion messages
- Tests assert Cyrillic output (not Dutch extraction)
- Different helper patterns
- Different ground truth approach (check for Cyrillic ratio rather than exact text matching)

**Assertion strategy for translations**: Use Cyrillic-ratio checks and key-term spot-checks rather than exact string matching, since translations can vary. Pattern from `translate_text/tests/e2e/.../test_product_box_quality.py`.

### Step 2: Create `test_contract.py`

Create `packages/translate_text_from_image/tests/integration/translate_text_from_image/test_contract.py` (~50-70 lines).

Contract tests:

1. **`test_prompt_asset_exists_and_loads`** — Verify `nl_ru.json` exists at the expected path and can be loaded by `load_prompt()`.

2. **`test_prompt_generator_reproduces_artifact`** — Run the prompt generator and compare output with committed `nl_ru.json`. Assert they match (SC-2 from spec).

3. **`test_supported_pairs_align_with_prompt_files`** — Verify that every pair in `_SUPPORTED_PAIRS` has a corresponding `<src>_<tgt>.json` prompt file.

4. **`test_shared_image_helper_used`** — Verify that `service.py` imports from `nl_processing.core.image_encoding` (not from `extract_text_from_image`). This is a static contract check — import the module and check.

### Step 3: Verify

Run the full integration test suite:
```bash
cd packages/translate_text_from_image && \
  doppler run -- env PYTHONPATH=src:../core/src \
  uv run pytest tests/integration -x -v
```

All tests must pass. If translation quality tests fail:
- Adjust the prompt examples in T5 (re-run prompt generator).
- Do NOT add fallbacks or workarounds in the service.

## Production safety constraints

- Uses live OpenAI API with project credentials (via doppler).
- API calls are stateless — no data mutations.
- No database operations.
- Same API key as production, but only for read-only inference calls.

## Anti-disaster constraints

- **Reuse before build**: Uses project's standard testing patterns and fixtures.
- **No regressions**: New test files only.
- **jscpd compliance**: Test content is unique (image-to-Russian-translation assertions).

## Error handling + correctness rules

- Tests explicitly verify error types (`TargetLanguageNotFoundError`), not just "some error."
- Tests verify `__cause__` is preserved on `APIError`.

## Zero legacy tolerance rule

- No legacy code involved. Fresh test suite.

## Acceptance criteria (testable)

1. `test_translation_accuracy.py` has at least 6 tests covering the scenarios listed above.
2. `test_contract.py` has at least 4 contract verification tests.
3. All tests pass against live API.
4. Simple sentence translation produces Cyrillic output.
5. Mixed-language image translates only Dutch content.
6. English-only image raises `TargetLanguageNotFoundError`.
7. Translation completes in < 10 seconds.
8. Output has no LLM chatter prefixes.
9. Prompt asset matches generator output.
10. All test files under 200 lines.

## Verification / quality gates

- [x] Integration tests pass with live API
- [x] Contract tests pass
- [x] Linters/formatters pass
- [x] jscpd: no 10+ line duplicates with other test files
- [x] All files under 200 lines

## Edge cases

- Network latency variation could cause flaky latency tests. The 10s gate is generous for a single API call.
- LLM output non-determinism: use Cyrillic-ratio checks and key-term matching rather than exact string comparison.
- Mixed-language synthetic images: Cyrillic renders as garbled in cv2 but the model should still recognize it as non-Dutch.

## Notes / risks

- **Risk**: LLM might translate English text in the "English-only" test instead of returning empty/raising error.
  - **Mitigation**: The prompt has 3 negative English-only examples teaching the model to return empty. If the test fails, add more negative examples to the prompt.
- **Risk**: Multiline structure may not be perfectly preserved.
  - **Mitigation**: Check for "more than one line in output" rather than exact line-for-line correspondence.
