---
Task ID: `T4`
Title: `Implement synthetic benchmark utilities`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T2`
Parallelizable: `yes, with T3`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create `nl_processing/extract_text_from_image/benchmark.py` containing three internal utilities: (1) a synthetic test image generator using OpenCV, (2) an extraction quality evaluator that compares extracted text against ground truth after normalization, and (3) a model comparison runner. These are internal dev tools — not part of the public interface — used by integration tests and for model selection. After this task, deterministic test images with known Dutch text can be generated and extraction accuracy can be measured.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — ETI-FR10 (synthetic image generator), ETI-FR11 (quality evaluator), ETI-FR12 (normalization), ETI-FR13 (model comparison runner)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — "Synthetic Benchmark System (Internal)"
- Epics: `docs/planning-artifacts/epics.md` — Story 2.3: Synthetic Benchmark System

## Preconditions

- T2 completed — `service.py` with `ImageTextExtractor` exists (needed by model comparison runner)
- T1 completed — `opencv-python` installed

## Non-goals

- These are internal utilities, not public API — no docstring completeness requirements beyond basic clarity
- No CLI interface — functions are called from tests or ad-hoc scripts
- No comprehensive benchmark data — just the utility functions. Actual test cases are defined in T5/T6.

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/extract_text_from_image/benchmark.py` (create)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/`
- `nl_processing/extract_text_from_image/service.py` (already implemented in T2/T3)
- `nl_processing/extract_text_from_image/__init__.py`
- `nl_processing/extract_text_from_image/image_encoding.py`
- Any other module's code or tests
- `tests/`
- `pyproject.toml`
- Any docs outside `docs/sprints/module-extract-text-from-image/`

**Test scope:**
- No automated tests for the benchmark utilities themselves (they are dev tools)
- They will be used by integration tests in T6
- Manual verification: generate an image, visually inspect, run evaluator

## Touched surface (expected files / modules)

- `nl_processing/extract_text_from_image/benchmark.py` — created

## Dependencies and sequencing notes

- Depends on T2 (service.py exists — needed for model comparison runner)
- Can run in parallel with T3 (error handling) — different files
- T5 (unit tests) uses the image generator for creating test fixtures
- T6 (integration tests) uses all three utilities

## Third-party / library research (mandatory for any external dependency)

- **Library**: `cv2` (opencv-python) — for synthetic image generation
  - **Text rendering**: `cv2.putText(img, text, org, fontFace, fontScale, color, thickness)`
    - `org` = bottom-left corner of text string
    - `fontFace` = e.g., `cv2.FONT_HERSHEY_SIMPLEX`
    - `fontScale` = font size multiplier
    - `color` = BGR tuple, e.g., `(0, 0, 0)` for black
    - `thickness` = line thickness in pixels
  - **Image creation**: `numpy.zeros((height, width, channels), dtype=numpy.uint8)` + `img.fill(255)` for white background
  - **Save to file**: `cv2.imwrite("output.png", img)`
  - **Known gotchas**:
    - `cv2.putText` renders text in a single line. For multi-line text, compute y-offset per line manually.
    - Font support is limited to built-in OpenCV fonts (Hershey). Special characters (Dutch: ë, ï, é, etc.) may not render correctly with OpenCV fonts. **Mitigation**: Use simple ASCII-representable Dutch text for synthetic images (e.g., "De kat zit op de mat" — no diacritics). Integration tests validate extraction, not font rendering.
    - `cv2.getTextSize()` can be used to measure text dimensions for proper layout.

- **Library**: `re` (stdlib) — for normalization
  - **Whitespace/markdown stripping**: `re.sub(r"[#*_~`>\-\s]+", " ", text).strip()`

## Implementation steps (developer-facing)

1. **Create `nl_processing/extract_text_from_image/benchmark.py`** with three functions:

   **a) Synthetic test image generator**:
   ```python
   import re
   import pathlib

   import cv2
   import numpy

   from nl_processing.core.models import Language
   from nl_processing.extract_text_from_image.service import ImageTextExtractor


   def generate_test_image(
       text: str,
       output_path: str,
       *,
       width: int = 800,
       height: int = 200,
       font_scale: float = 1.0,
       thickness: int = 2,
   ) -> str:
       """Generate a synthetic test image with known text rendered on it.

       Returns the output file path.
       """
       img = numpy.zeros((height, width, 3), dtype=numpy.uint8)
       img.fill(255)  # white background

       lines = text.split("\n")
       y_offset = 40
       line_height = int(40 * font_scale)

       for line in lines:
           cv2.putText(
               img, line, (20, y_offset),
               cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness,
           )
           y_offset += line_height

       cv2.imwrite(output_path, img)
       return output_path
   ```

   **b) Extraction quality evaluator**:
   ```python
   def normalize_text(text: str) -> str:
       """Normalize text for comparison: strip whitespace, line breaks, markdown formatting."""
       normalized = re.sub(r"[#*_~`>\-]+", "", text)  # remove markdown chars
       normalized = re.sub(r"\s+", " ", normalized)    # collapse whitespace
       return normalized.strip().lower()


   def evaluate_extraction(extracted: str, ground_truth: str) -> bool:
       """Compare extracted text against ground truth after normalization.

       Returns True if exact match after normalization.
       """
       return normalize_text(extracted) == normalize_text(ground_truth)
   ```

   **c) Model comparison runner**:
   ```python
   def run_benchmark(
       test_cases: list[tuple[str, str]],
       *,
       model: str = "gpt-5-nano",  # GPT-5 Mini is evaluation baseline
       language: Language = Language.NL,
   ) -> list[dict[str, str | bool]]:
       """Run the benchmark suite against a specified model.

       Args:
           test_cases: List of (image_path, ground_truth_text) tuples.
           model: LLM model name.
           language: Target language.

       Returns:
           List of result dicts with keys: image_path, ground_truth, extracted, passed.
       """
       extractor = ImageTextExtractor(language=language, model=model)
       results: list[dict[str, str | bool]] = []
       for image_path, ground_truth in test_cases:
           extracted = extractor.extract_from_path(image_path)
           passed = evaluate_extraction(extracted, ground_truth)
           results.append({
               "image_path": image_path,
               "ground_truth": ground_truth,
               "extracted": extracted,
               "passed": passed,
           })
       return results
   ```

2. **Verify file size** — ensure `benchmark.py` is under 200 lines.

3. **Run linting**: `uv run ruff format nl_processing/extract_text_from_image/benchmark.py && uv run ruff check nl_processing/extract_text_from_image/benchmark.py`

4. **Manual verification** (optional):
   ```bash
   uv run python -c "
   from nl_processing.extract_text_from_image.benchmark import generate_test_image, normalize_text, evaluate_extraction
   generate_test_image('Hallo wereld', '/tmp/test_nl.png')
   print('Image generated')
   print(normalize_text('# Hello **world**'))
   print(evaluate_extraction('Hello world', '# Hello **world**'))
   "
   ```

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: The image generator writes to caller-specified paths. Tests will use `tmp_path` or `/tmp/`. No production file paths.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses OpenCV (already a dependency) for image generation — no custom image libraries.
- **Correct libraries only**: `opencv-python` from `pyproject.toml`, `re` from stdlib.
- **Correct file locations**: `benchmark.py` within the module, per architecture spec.
- **No regressions**: New file — no existing functionality affected.

## Error handling + correctness rules (mandatory)

- `generate_test_image` — if `cv2.imwrite` fails, it returns `False` (not an exception). Check return value and raise `ValueError` if the write fails.
- `run_benchmark` — if any extraction fails (API error, etc.), let the exception propagate. Do not catch and silence benchmark failures.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — new file.

## Acceptance criteria (testable)

1. `from nl_processing.extract_text_from_image.benchmark import generate_test_image, normalize_text, evaluate_extraction, run_benchmark` succeeds
2. `generate_test_image("Hello", "/tmp/test.png")` creates a readable PNG image at the specified path
3. `normalize_text("# Hello **world**")` returns `"hello world"`
4. `normalize_text("  multiple   spaces  \n\n  ")` returns `"multiple spaces"`
5. `evaluate_extraction("Hello world", "# Hello **world**")` returns `True`
6. `evaluate_extraction("Hello", "Goodbye")` returns `False`
7. `uv run ruff check nl_processing/extract_text_from_image/benchmark.py` passes
8. `benchmark.py` is under 200 lines

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Manual verification: generated image is visually readable

## Edge cases

- Multi-line text in image generation: each line needs a separate `putText` call with increasing y-offset.
- Empty text input to `generate_test_image` — generates a blank white image. This is valid (used for testing no-text scenarios).
- Empty string to `normalize_text` — returns `""`. This is correct.
- Normalization must handle: `#`, `*`, `_`, `~`, `` ` ``, `>`, `-`, multiple spaces, newlines, tabs.

## Rollout / rollback (if relevant)

- Rollout: Create the file.
- Rollback: Delete the file.

## Notes / risks

- **Risk**: OpenCV built-in fonts do not support Dutch diacritics (ë, ï, é). **Mitigation**: Use ASCII-only Dutch text for synthetic images (e.g., "De kat zit op de mat", "Dit is een test"). Diacritics are not essential for validating the extraction pipeline.
- **Risk**: Generated images may be too low quality for the Vision API to read. **Mitigation**: Use high contrast (black on white), large font size, and sufficient image dimensions. Start with simple single-line text and iterate.
- **Risk**: `vulture` may flag `run_benchmark` as unused (it's only called from integration tests or ad-hoc). **Mitigation**: Add to `vulture_whitelist.py` in T7 if needed.
