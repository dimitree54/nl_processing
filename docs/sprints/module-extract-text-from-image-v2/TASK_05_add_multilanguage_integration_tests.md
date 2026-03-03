---
Task ID: `T5`
Title: `Add multi-language integration tests (mixed Dutch+Russian, English-only)`
Sprint: `2026-03-03_extract-text-v2-modifications`
Module: `extract_text_from_image`
Depends on: `T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Add integration tests that verify the module correctly handles multi-language images (extracts only Dutch) and English-only images (raises `TargetLanguageNotFoundError`). These tests make real OpenAI API calls and validate the end-to-end behavior of the few-shot prompt introduced in T3.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md`
  - FR3: "Module extracts only text in the specified target language from the image"
  - FR4: "Module ignores text in languages other than the target language"
  - FR7: "Module raises TargetLanguageNotFoundError when no text in the target language is detected"
- Architecture: `docs/planning-artifacts/architecture.md` § "Test Organization" — "Integration tests: real API calls, validate prompt quality"

## Preconditions

- T4 complete — all unit tests pass, linting clean, module works with new prompt.
- `OPENAI_API_KEY` is available via Doppler for integration tests.

## Non-goals

- Do not modify any production code.
- Do not add unit tests (those already exist and pass).
- Do not modify existing integration tests — only add new ones.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` — add new test functions

**FORBIDDEN — this task must NEVER touch:**
- Any production code (`nl_processing/`)
- Any unit test files
- Any other module's tests
- `pyproject.toml`, `ruff.toml`, `Makefile`

**Test scope:**
- Tests go in: `tests/integration/extract_text_from_image/`
- Test command: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`

## Touched surface (expected files / modules)

- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` (76 lines → ~130 lines)

## Dependencies and sequencing notes

- Depends on T4 because the new prompt must be verified working before testing with real API calls.
- This is the final task — no downstream dependencies.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries. Uses existing:

- `pytest` + `pytest.mark.asyncio` — already used in the file
- `nl_processing.extract_text_from_image.benchmark.generate_test_image()` — already used
- `nl_processing.extract_text_from_image.service.ImageTextExtractor` — already used
- `nl_processing.core.exceptions.TargetLanguageNotFoundError` — already imported in test_error_handling.py, will need to import here
- `nl_processing.core.models.Language` — already imported in the file

### `generate_test_image()` and Cyrillic text

- `cv2.FONT_HERSHEY_SIMPLEX` does NOT render Cyrillic characters properly — they appear as `?` or blank boxes.
- For the mixed Dutch+Russian test, the Russian text will appear as garbled characters in the image. The model should still recognize it as non-Dutch and extract only the Dutch portion.
- For the English-only test, Latin characters render correctly.

## Implementation steps (developer-facing)

### Step 1: Add imports

At the top of `tests/integration/extract_text_from_image/test_extraction_accuracy.py`, add the import for `TargetLanguageNotFoundError` (it's not currently imported in this file):

```python
from nl_processing.core.exceptions import TargetLanguageNotFoundError
```

### Step 2: Add test for mixed Dutch + Russian text

Add the following test function after the existing tests:

```python
@pytest.mark.asyncio
async def test_mixed_dutch_russian_extracts_only_dutch(tmp_path: pathlib.Path) -> None:
    """Image with mixed Dutch + Russian text — only Dutch text should be extracted (FR3, FR4)."""
    dutch_text = "Welkom bij ons"
    # Russian text renders as garbled chars in cv2, but the model should recognize
    # it as non-Dutch content and exclude it from extraction.
    mixed_text = f"{dutch_text}\nДобро пожаловать"
    image_path = str(tmp_path / "mixed_lang.png")
    generate_test_image(mixed_text, image_path, font_scale=1.2, width=800, height=200)

    extractor = ImageTextExtractor(language=Language.NL)
    extracted = await extractor.extract_from_path(image_path)

    # The extracted text should contain only the Dutch portion
    assert evaluate_extraction(extracted, dutch_text), (
        f"Mixed-language extraction failed.\n"
        f"Expected (Dutch only): {dutch_text}\n"
        f"Got: {extracted}"
    )
```

### Step 3: Add test for English-only text

```python
@pytest.mark.asyncio
async def test_english_only_raises_target_language_not_found(tmp_path: pathlib.Path) -> None:
    """Image with English-only text — should raise TargetLanguageNotFoundError (FR7)."""
    english_text = "The quick brown fox jumps over the lazy dog"
    image_path = str(tmp_path / "english_only.png")
    generate_test_image(english_text, image_path, font_scale=1.2, width=800, height=100)

    extractor = ImageTextExtractor(language=Language.NL)

    with pytest.raises(TargetLanguageNotFoundError, match="No text in the target language"):
        await extractor.extract_from_path(image_path)
```

### Step 4: Verify file stays under 200 lines

After adding the two tests, the file should be ~120-130 lines. Well under the 200-line limit.

### Step 5: Lint

```bash
uv run ruff check tests/integration/extract_text_from_image/
```

### Step 6: Run integration tests

```bash
doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v
```

**Expected results:**
- All existing tests pass (simple Dutch, multi-line Dutch, cv2 array, latency)
- `test_mixed_dutch_russian_extracts_only_dutch` — passes (Dutch text extracted, Russian ignored)
- `test_english_only_raises_target_language_not_found` — passes (`TargetLanguageNotFoundError` raised)

### Step 7: Final `make check`

```bash
doppler run -- make check
```

This runs the full pipeline: ruff, pylint, vulture, jscpd, all unit tests, all integration tests, all e2e tests. **Everything must pass.**

## Production safety constraints (mandatory)

- Integration tests make real OpenAI API calls (paid). This is expected and necessary per architecture doc.
- Tests use Doppler-managed `OPENAI_API_KEY` (not production credentials — same key, but used for testing).
- No database operations.
- No shared resources.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses existing `generate_test_image()`, `evaluate_extraction()`, `ImageTextExtractor` — no new utilities.
- **Correct libraries only**: No new imports beyond what's already used in the project.
- **Correct file locations**: Tests added to existing integration test file.
- **No regressions**: Existing integration tests continue to pass unchanged.

## Error handling + correctness rules (mandatory)

- The `test_english_only_raises_target_language_not_found` test explicitly asserts that `TargetLanguageNotFoundError` is raised — it tests the error path, not silencing it.
- No try/except in test code (pytest's `raises` context manager handles assertion).

## Zero legacy tolerance rule (mandatory)

- No old code to remove. These are purely additive tests.

## Acceptance criteria (testable)

1. `test_mixed_dutch_russian_extracts_only_dutch` exists in `test_extraction_accuracy.py`
2. `test_english_only_raises_target_language_not_found` exists in `test_extraction_accuracy.py`
3. `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v` — all tests pass (including new ones)
4. `doppler run -- make check` — passes completely (the final quality gate)
5. `test_extraction_accuracy.py` is under 200 lines
6. No lint errors in the file

## Verification / quality gates

- [ ] `uv run ruff check tests/integration/extract_text_from_image/` — zero errors
- [ ] `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v` — all tests pass
- [ ] `doppler run -- make check` — passes (FINAL GATE for the entire sprint)
- [ ] New tests specifically validate FR3, FR4, FR7

## Edge cases

- **Cyrillic rendering**: `generate_test_image()` uses OpenCV's `FONT_HERSHEY_SIMPLEX` which doesn't support Cyrillic. The Russian text will appear as `?` characters or boxes. The model may describe this as "garbled text" or "unknown characters" — either way, it should not be included in the Dutch extraction output.
- **Model variability**: The LLM may sometimes include minor variations (e.g., different whitespace). The `evaluate_extraction()` function normalizes whitespace, markdown, and case before comparison, so minor formatting differences are tolerated.
- **Rate limiting**: If running many integration tests in quick succession, OpenAI may rate-limit. The tests run sequentially with `-x` flag, and the small number of tests (6 total) is unlikely to trigger rate limits.
- **API latency**: The new prompt with few-shot examples (including base64 images) is larger than the old prompt. This may increase latency slightly. The existing `test_extraction_latency` test has a 1-second threshold — monitor if this becomes an issue. If latency increases significantly due to the larger prompt, this is a signal to optimize image sizes in T3.

## Notes / risks

- **Risk**: The mixed Dutch+Russian test may be flaky because the model might interpret garbled Cyrillic differently each time.
  - **Mitigation**: The few-shot examples in the prompt (T3) explicitly teach the model to ignore non-Dutch text. The `evaluate_extraction()` comparison is normalized. If flakiness occurs, adjust the test to be more lenient (e.g., assert Dutch text is present rather than exact match).
- **Risk**: The English-only test depends on the model returning empty text (which triggers `TargetLanguageNotFoundError` in `service.py`).
  - **Mitigation**: The few-shot Example 3 explicitly demonstrates that English-only images should produce `text: ""`. The `service.py` raises `TargetLanguageNotFoundError` when `result.text.strip()` is empty. This should be reliable.
- **Risk**: Real API costs. Each integration test makes one API call.
  - **Mitigation**: 2 new tests = 2 additional API calls per test run. Cost is negligible (~$0.01 per run with gpt-4.1-mini).
