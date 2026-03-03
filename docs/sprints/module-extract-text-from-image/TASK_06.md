---
Task ID: `T6`
Title: `Create integration and e2e tests`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create integration tests (real OpenAI API calls with synthetic test images) and e2e tests (full extraction scenarios) for the `extract_text_from_image` module. Integration tests validate extraction accuracy at 100% exact match after normalization on the synthetic test suite. E2e tests validate full pipeline scenarios including multi-format support and error scenarios with real images. After this task, the module's extraction quality is verified against real LLM output.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — ETI-FR1-6 (extraction accuracy), ETI-NFR1 (≤1s latency), ETI-NFR3 (all supported formats)
- Shared: `docs/planning-artifacts/prd.md` — SNFR17 (all test levels must pass), SNFR18 (integration tests run regularly)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — "Test Strategy" (integration: real API + synthetic images, e2e: full scenarios)
- Epics: `docs/planning-artifacts/epics.md` — Story 2.3: Synthetic Benchmark System & Integration Tests

## Preconditions

- T5 completed — unit tests pass, all module code is verified at the mock level
- T2-T4 completed — service, error handling, and benchmark utilities all exist
- `OPENAI_API_KEY` available via Doppler (required for real API calls)

## Non-goals

- No modification of source code — tests only
- No new benchmark utilities (T4 already created them)
- No testing of other modules

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `tests/integration/extract_text_from_image/__init__.py` (create)
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` (create)
- `tests/e2e/extract_text_from_image/__init__.py` (create)
- `tests/e2e/extract_text_from_image/test_full_extraction.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/` (any source code)
- `tests/unit/` (already done in T5)
- `tests/integration/core/`, `tests/e2e/core/` (owned by module-core sprint)
- Any other module's test directories
- `pyproject.toml`
- Any docs outside `docs/sprints/module-extract-text-from-image/`

**Test scope:**
- Integration tests: `tests/integration/extract_text_from_image/`
- E2e tests: `tests/e2e/extract_text_from_image/`
- Integration command: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`
- E2e command: `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v`

## Touched surface (expected files / modules)

- `tests/integration/extract_text_from_image/__init__.py` — created (empty)
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` — created
- `tests/e2e/extract_text_from_image/__init__.py` — created (empty)
- `tests/e2e/extract_text_from_image/test_full_extraction.py` — created

## Dependencies and sequencing notes

- Depends on T5 (unit tests pass — code is stable)
- T7 (final verification) depends on this task
- Integration and e2e tests require `OPENAI_API_KEY` — must run with `doppler run --`

## Third-party / library research (mandatory for any external dependency)

- **OpenAI API usage**: Real API calls are made. Each test image extraction uses one Vision API call.
  - **Rate limits**: OpenAI standard rate limits apply. Keep test suite small (3-5 test cases) to avoid rate limiting.
  - **Cost**: Each Vision API call costs ~$0.01-0.05 depending on image size and model. Budget for ~10 calls per test run.
  - **Documentation**: https://platform.openai.com/docs/guides/vision

- **pytest timing**: Use `time.time()` or pytest's built-in timing to verify ≤1s latency per extraction.

## Implementation steps (developer-facing)

1. **Create `tests/integration/extract_text_from_image/` directory and `__init__.py`** (empty).

2. **Create `tests/integration/extract_text_from_image/test_extraction_accuracy.py`**:

   **Test cases** — generate 3-5 synthetic images with known Dutch text, extract, validate 100% exact match after normalization:

   ```python
   import pathlib
   import time

   from nl_processing.core.models import Language
   from nl_processing.extract_text_from_image.benchmark import (
       evaluate_extraction,
       generate_test_image,
   )
   from nl_processing.extract_text_from_image.service import ImageTextExtractor


   def test_simple_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
       """Single line of simple Dutch text — baseline accuracy test."""
       ground_truth = "De kat zit op de mat"
       image_path = str(tmp_path / "simple.png")
       generate_test_image(ground_truth, image_path, font_scale=1.5, width=800, height=100)

       extractor = ImageTextExtractor(language=Language.NL)
       extracted = extractor.extract_from_path(image_path)

       assert evaluate_extraction(extracted, ground_truth), (
           f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
       )


   def test_multi_line_dutch_text_extraction(tmp_path: pathlib.Path) -> None:
       """Multi-line Dutch text — tests line break handling."""
       ground_truth = "Dit is een test\nvan meerdere regels"
       image_path = str(tmp_path / "multiline.png")
       generate_test_image(ground_truth, image_path, font_scale=1.2, width=800, height=200)

       extractor = ImageTextExtractor(language=Language.NL)
       extracted = extractor.extract_from_path(image_path)

       assert evaluate_extraction(extracted, ground_truth), (
           f"Extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
       )


   def test_extraction_from_cv2_array(tmp_path: pathlib.Path) -> None:
       """Test extract_from_cv2 produces same result as extract_from_path."""
       import cv2

       ground_truth = "Hallo wereld"
       image_path = str(tmp_path / "cv2test.png")
       generate_test_image(ground_truth, image_path, font_scale=1.5, width=600, height=100)

       cv2_image = cv2.imread(image_path)
       extractor = ImageTextExtractor(language=Language.NL)
       extracted = extractor.extract_from_cv2(cv2_image)

       assert evaluate_extraction(extracted, ground_truth), (
           f"CV2 extraction mismatch.\nExpected: {ground_truth}\nGot: {extracted}"
       )


    def test_extraction_latency(tmp_path: pathlib.Path) -> None:
        """Each extraction call completes in < 10 seconds (ETI-NFR1)."""
       ground_truth = "Snel test"
       image_path = str(tmp_path / "latency.png")
       generate_test_image(ground_truth, image_path, font_scale=1.5, width=400, height=100)

       extractor = ImageTextExtractor(language=Language.NL)
       start = time.time()
       extractor.extract_from_path(image_path)
       elapsed = time.time() - start

        # Integration tests make real API calls; network latency is included.
        assert elapsed < 10, f"Extraction took {elapsed:.2f}s — exceeds timeout"
   ```

3. **Create `tests/e2e/extract_text_from_image/` directory and `__init__.py`** (empty).

4. **Create `tests/e2e/extract_text_from_image/test_full_extraction.py`**:

   **Full extraction scenarios** — test the module end-to-end including error cases with real images:

   ```python
   import pathlib

   import numpy
   import pytest

   from nl_processing.core.exceptions import TargetLanguageNotFoundError, UnsupportedImageFormatError
   from nl_processing.core.models import Language
   from nl_processing.extract_text_from_image.benchmark import generate_test_image
   from nl_processing.extract_text_from_image.service import ImageTextExtractor


   def test_full_dutch_extraction_pipeline(tmp_path: pathlib.Path) -> None:
       """End-to-end: generate image → extract → verify content."""
       text = "Nederland is een mooi land"
       image_path = str(tmp_path / "e2e.png")
       generate_test_image(text, image_path, font_scale=1.5, width=800, height=100)

       extractor = ImageTextExtractor()
       result = extractor.extract_from_path(image_path)

       assert isinstance(result, str)
       assert len(result.strip()) > 0


   def test_unsupported_format_raises_error(tmp_path: pathlib.Path) -> None:
       """E2e: unsupported format raises UnsupportedImageFormatError immediately."""
       bmp_path = str(tmp_path / "test.bmp")
       pathlib.Path(bmp_path).write_bytes(b"fake bmp content")

       extractor = ImageTextExtractor()
       with pytest.raises(UnsupportedImageFormatError):
           extractor.extract_from_path(bmp_path)


   def test_blank_image_raises_target_language_not_found(tmp_path: pathlib.Path) -> None:
       """E2e: blank image with no text raises TargetLanguageNotFoundError."""
       import cv2

       blank = numpy.zeros((100, 400, 3), dtype=numpy.uint8)
       blank.fill(255)
       blank_path = str(tmp_path / "blank.png")
       cv2.imwrite(blank_path, blank)

       extractor = ImageTextExtractor()
       with pytest.raises(TargetLanguageNotFoundError):
           extractor.extract_from_path(blank_path)


   def test_supported_image_formats(tmp_path: pathlib.Path) -> None:
       """E2e: verify PNG, JPEG, WebP formats are accepted (no format error)."""
       import cv2

       img = numpy.zeros((100, 400, 3), dtype=numpy.uint8)
       img.fill(255)
       cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)

       for ext in [".png", ".jpg", ".webp"]:
           path = str(tmp_path / f"test{ext}")
           cv2.imwrite(path, img)
           extractor = ImageTextExtractor()
           # Should not raise UnsupportedImageFormatError
           # May raise TargetLanguageNotFoundError or return text — both are valid
           try:
               extractor.extract_from_path(path)
           except TargetLanguageNotFoundError:
               pass  # Expected — "Test" is English, not Dutch
   ```

5. **Run integration tests**: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`

6. **Run e2e tests**: `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v`

7. **Run linting**: `uv run ruff format tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/ && uv run ruff check tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Uses `OPENAI_API_KEY` from Doppler dev environment — NOT the production environment. Doppler environments are separate.
- **Migration preparation**: N/A.
- **API costs**: Integration/e2e tests make real paid API calls. Budget ~$0.50 per full test run.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses the benchmark utilities from T4 for image generation and evaluation.
- **Correct libraries only**: `pytest`, `cv2`, `numpy` — all already in dependencies.
- **Correct file locations**: Tests in `tests/integration/extract_text_from_image/` and `tests/e2e/extract_text_from_image/`.
- **No regressions**: New test files — no existing tests affected.

## Error handling + correctness rules (mandatory)

- Tests must assert specific outcomes — no silent passes.
- Use `pytest.raises()` for expected exceptions.
- Integration tests that make API calls may be flaky due to network — document this risk. Do NOT add `pytest.mark.skip` or `pytest.mark.flaky` (banned).

## Zero legacy tolerance rule (mandatory)

- No legacy tests exist (old broken test was deleted in T1).

## Acceptance criteria (testable)

1. `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v` passes (all integration tests green)
2. `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v` passes (all e2e tests green)
3. Integration tests achieve 100% exact match after normalization on synthetic test images
4. E2e tests cover: full pipeline, unsupported format error, blank image error, multiple supported formats
5. `uv run ruff check tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/` passes
6. All test files are under 200 lines
7. Integration tests run with `doppler run --` prefix (need `OPENAI_API_KEY`)

## Verification / quality gates

- [ ] Integration tests pass with real API calls
- [ ] E2e tests pass with real API calls
- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Negative-path tests exist (unsupported format, blank image)

## Edge cases

- Network timeout during API call — test may fail due to external factors, not code bugs. Re-run if needed. Do NOT skip.
- Vision API rate limit — keep test suite small (3-5 integration, 3-4 e2e). Run sequentially (no `-n auto` for integration/e2e).
- Synthetic image quality — if the Vision API cannot read OpenCV-generated text, increase font size and image dimensions. Iterate on `generate_test_image` parameters.
- The latency test uses a generous 10s timeout to account for network variability, while the NFR specifies ≤1s excluding network. Document this compromise.

## Rollout / rollback (if relevant)

- Rollout: Create test files in a single commit.
- Rollback: Delete the test files.

## Notes / risks

- **Risk**: Integration tests are paid and slow (~1-3s per API call). **Mitigation**: Keep the test suite small (3-5 test cases). Run with `-x` to fail fast.
- **Risk**: Synthetic images generated with OpenCV fonts may not be readable by the Vision API. **Mitigation**: Use large fonts (font_scale ≥ 1.5), high contrast (black on white), generous image dimensions. If tests fail, adjust image parameters before changing code.
- **Risk**: The blank image test may not reliably trigger `TargetLanguageNotFoundError` — the LLM might return descriptive text about the blank image. **Mitigation**: The prompt instructs the model to return only Dutch text. If the LLM returns empty text, the error is raised. If it returns non-Dutch descriptive text, the test may need adjustment. This is an integration-level concern that validates prompt quality.
