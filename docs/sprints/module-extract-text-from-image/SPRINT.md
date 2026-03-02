---
Sprint ID: `2026-03-02_module-extract-text-from-image`
Sprint Goal: `Deliver the extract_text_from_image module: ImageTextExtractor service, Dutch prompt, error handling, benchmark utilities, and full test suite`
Sprint Type: `module`
Module: `extract_text_from_image`
Status: `planning`
Owners: `Developer`
---

## Goal

Implement the `nl_processing/extract_text_from_image/` module providing `ImageTextExtractor` — a service class that extracts language-specific text from images using OpenAI Vision API. The module accepts images as file paths or OpenCV `numpy.ndarray` arrays, returns clean markdown-formatted text via LangChain structured output, and includes a Dutch extraction prompt (`prompts/nl.json`). Includes format validation, typed error handling, synthetic benchmark utilities, and a comprehensive test suite (unit, integration, e2e). Replaces the existing mock `service.py` and broken `__init__.py`.

## Module Scope

### What this sprint implements
- Module: `extract_text_from_image` — image-to-text extraction using OpenAI Vision API
- Architecture spec: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `nl_processing/extract_text_from_image/__init__.py` (make empty — currently has re-exports)
- `nl_processing/extract_text_from_image/service.py` (rewrite — currently has mock function)
- `nl_processing/extract_text_from_image/image_encoding.py` (create — if service.py would exceed 200 lines)
- `nl_processing/extract_text_from_image/benchmark.py` (create — synthetic benchmark utilities)
- `nl_processing/extract_text_from_image/prompts/nl.json` (create — Dutch extraction prompt)
- `tests/unit/extract_text_from_image/__init__.py` (exists — keep or recreate)
- `tests/unit/extract_text_from_image/test_extract_text_from_image.py` (rewrite — currently broken)
- `tests/unit/extract_text_from_image/test_image_encoding.py` (create if needed)
- `tests/unit/extract_text_from_image/test_error_handling.py` (create if needed)
- `tests/integration/extract_text_from_image/__init__.py` (create)
- `tests/integration/extract_text_from_image/test_extraction_accuracy.py` (create)
- `tests/e2e/extract_text_from_image/__init__.py` (create)
- `tests/e2e/extract_text_from_image/test_full_extraction.py` (create)
- `pyproject.toml` (modify — add `opencv-python` dependency)
- `vulture_whitelist.py` (modify if needed)

**FORBIDDEN — this sprint must NEVER touch:**
- `nl_processing/core/` (owned by module-core sprint — already implemented)
- `nl_processing/extract_words_from_text/` (owned by future sprint)
- `nl_processing/translate_text/` (owned by future sprint)
- `nl_processing/translate_word/` (owned by future sprint)
- `nl_processing/database/` (out of scope)
- `nl_processing/__init__.py` (owned by module-core sprint — already emptied)
- Any docs outside `docs/sprints/module-extract-text-from-image/`
- Requirements/architecture docs
- `Makefile`, `ruff.toml`, `pytest.ini`

### Test Scope
- **Unit test directory**: `tests/unit/extract_text_from_image/`
- **Integration test directory**: `tests/integration/extract_text_from_image/`
- **E2e test directory**: `tests/e2e/extract_text_from_image/`
- **Unit test command**: `uv run pytest tests/unit/extract_text_from_image/ -x -v`
- **Integration test command**: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`
- **E2e test command**: `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v`
- **Full module test command**: `uv run pytest tests/unit/extract_text_from_image/ tests/integration/extract_text_from_image/ tests/e2e/extract_text_from_image/ -x -v`
- **NEVER run**: `uv run pytest` (full suite) or tests from other modules

## Interface Contract

### Public interface this sprint implements

```python
# nl_processing/extract_text_from_image/service.py
from nl_processing.core.models import Language

class ImageTextExtractor:
    def __init__(self, *, language: Language = Language.NL, model: str = "gpt-5-mini") -> None:
        ...

    def extract_from_path(self, path: str) -> str:
        """Extract text from image at the given file path. Returns markdown-formatted text."""
        ...

    def extract_from_cv2(self, image: "numpy.ndarray") -> str:
        """Extract text from OpenCV image array. Returns markdown-formatted text."""
        ...
```

### Exceptions raised
- `UnsupportedImageFormatError` — image format not supported by OpenAI Vision API (raised before API call)
- `TargetLanguageNotFoundError` — no text in target language found, or image contains no text
- `APIError` — wraps upstream LangChain/OpenAI API errors

### Imports from core (dependencies on module-core sprint)
- `from nl_processing.core.models import Language, ExtractedText`
- `from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError, UnsupportedImageFormatError`
- `from nl_processing.core.prompts import load_prompt` (optional — may load directly)

## Scope

### In
- `ImageTextExtractor` class with `extract_from_path()` and `extract_from_cv2()` methods
- Dutch extraction prompt at `prompts/nl.json` (CFR11, SFR6)
- Image format validation: PNG, JPEG, GIF, WebP supported; others raise `UnsupportedImageFormatError` (ETI-FR8)
- Image → base64 encoding pipeline (ETI-FR1, ETI-FR2)
- OpenAI Vision API integration via LangChain `HumanMessage` with image content parts
- `with_structured_output()` via `ExtractedText` model from core (SFR1)
- Error handling: `TargetLanguageNotFoundError` for no target text (ETI-FR7, ETI-FR9), `APIError` wrapping (SFR9-10)
- Synthetic benchmark utilities: image generator, quality evaluator, model comparison runner (ETI-FR10-13)
- Add `opencv-python` dependency to `pyproject.toml` (ETI-NFR4)
- Unit tests: mock chain, test encoding, format validation, error mapping
- Integration tests: real API calls with synthetic images, 100% exact match after normalization
- E2e tests: full extraction scenarios
- Clean up: empty `__init__.py`, rewrite broken test file

### Out
- No languages other than Dutch (interface supports them, only NL prompt implemented)
- No video processing, batch processing, caching
- No PIL.Image or raw bytes input support
- No CI pipeline changes
- No Doppler configuration changes

## Inputs (contracts)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` (ETI-FR1-13, ETI-NFR1-4)
- Shared requirements: `docs/planning-artifacts/prd.md` (SFR1-14, SNFR1-19)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md`
- Shared architecture: `docs/planning-artifacts/architecture.md` (code style, patterns, error handling)
- Epics: `docs/planning-artifacts/epics.md` (Epic 2: Stories 2.1, 2.2, 2.3)
- Related constraints: `ruff.toml`, `Makefile`

## Change digest

- **Requirement deltas**: None — first implementation of this module
- **Architecture deltas**: None — implementing as specified

## Task list (dependency-aware)

- **T1:** `TASK_01.md` (depends: —) (parallel: no) — Clean up broken files: empty `__init__.py`, add `opencv-python` dependency
- **T2:** `TASK_02.md` (depends: T1) (parallel: no) — Implement ImageTextExtractor service with Dutch prompt and image encoding
- **T3:** `TASK_03.md` (depends: T2) (parallel: no) — Implement error handling: format validation, TargetLanguageNotFoundError, APIError wrapping
- **T4:** `TASK_04.md` (depends: T2) (parallel: yes, with T3) — Implement synthetic benchmark utilities
- **T5:** `TASK_05.md` (depends: T3) (parallel: no) — Create unit tests
- **T6:** `TASK_06.md` (depends: T5) (parallel: no) — Create integration and e2e tests
- **T7:** `TASK_07.md` (depends: T5, T6) (parallel: no) — Final verification: make check passes

## Dependency graph (DAG)

- T1 → T2
- T2 → T3
- T2 → T4
- T3 → T5
- T4 → T5 (benchmark utilities needed for test image generation)
- T5 → T6
- T5 → T7
- T6 → T7

## Execution plan

### Critical path
- T1 → T2 → T3 → T5 → T6 → T7

### Parallel tracks (lanes)
- **Lane A**: T3 (error handling) — after T2
- **Lane B**: T4 (benchmark utilities) — after T2
- Lane A and B can run in parallel. T5 waits for both.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. This module has no database interactions.
- **Shared resource isolation**: Module is a library — no ports, sockets, or file paths at runtime. Tests run in-process only. Integration/e2e tests use `OPENAI_API_KEY` via Doppler (dev environment) — production API key is in a separate Doppler environment.
- **Migration deliverable**: N/A — no data model changes

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Unit tests pass: `uv run pytest tests/unit/extract_text_from_image/ -x -v`
- Integration tests pass: `doppler run -- uv run pytest tests/integration/extract_text_from_image/ -x -v`
- E2e tests pass: `doppler run -- uv run pytest tests/e2e/extract_text_from_image/ -x -v`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches architecture spec exactly (`ImageTextExtractor` with `extract_from_path`, `extract_from_cv2`)
- Zero legacy tolerance: mock `service.py` replaced, broken `__init__.py` emptied, broken test rewritten
- No errors are silenced (no swallowed exceptions)
- Requirements/architecture docs unchanged
- Production database untouched
- No shared local resources conflict with production instance
- `nl_processing/extract_text_from_image/__init__.py` is empty (ruff compliant)

## Risks + mitigations

- **Risk**: OpenAI Vision API response format may vary — `ExtractedText` structured output may not always extract cleanly.
  - **Mitigation**: `with_structured_output()` enforces the Pydantic schema. Integration tests validate 100% exact match on synthetic images.
- **Risk**: Synthetic test images may not produce clear enough text for the Vision API.
  - **Mitigation**: Use high-contrast black-on-white text with a large font. Start with simple single-line text, iterate if needed.
- **Risk**: `TargetLanguageNotFoundError` detection requires post-extraction logic — the LLM may return an empty `text` field or describe that no text was found.
  - **Mitigation**: Check if `ExtractedText.text` is empty or whitespace-only after extraction. If so, raise `TargetLanguageNotFoundError`.
- **Risk**: OpenAI API rate limits during integration tests.
  - **Mitigation**: Keep synthetic test suite small (3-5 images). Run integration tests sequentially (no `-n auto`).
- **Risk**: `opencv-python` installation may be problematic on some platforms.
  - **Mitigation**: `opencv-python` is a well-maintained package with pre-built wheels for all major platforms. `uv sync` handles installation.

## Migration plan (if data model changes)

N/A — no data model changes

## Rollback / recovery notes

- Revert all files in ALLOWED list to their previous state via git.
- No database or external state to roll back.

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4` → `T5` → `T6` → `T7`
- Validator: `task-checker`
- Outcome: `pending`
- Notes: —

## Sources used

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md`, `docs/planning-artifacts/prd.md`
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md`, `docs/planning-artifacts/architecture.md`
- Epics: `docs/planning-artifacts/epics.md` (Epic 2)
- Product brief: `nl_processing/extract_text_from_image/docs/product-brief-extract_text_from_image-2026-03-01.md`
- Code read: `nl_processing/extract_text_from_image/__init__.py`, `nl_processing/extract_text_from_image/service.py`, `tests/unit/extract_text_from_image/test_extract_text_from_image.py`, `pyproject.toml`, `ruff.toml`, `Makefile`, `vulture_whitelist.py`

## Contract summary

### What (requirements)
- ETI-FR1-2: Two input methods (`extract_from_path`, `extract_from_cv2`) → markdown-formatted string
- ETI-FR3-6: Language-specific extraction, markdown structure preservation
- ETI-FR7-9: `TargetLanguageNotFoundError` for no target text / no text at all, `UnsupportedImageFormatError` for bad formats
- ETI-FR10-13: Synthetic benchmark system (image generator, quality evaluator, model comparison)
- ETI-NFR1-4: ≤1s latency, all OpenAI Vision formats supported, `opencv-python` dependency

### How (architecture)
- OpenAI Vision API: image as base64 in `HumanMessage` with image content parts
- Two inputs converge to same internal pipeline after base64 encoding
- Format validation before API call — fail fast
- `with_structured_output()` via `ExtractedText` from core
- Each module instantiates its own `ChatOpenAI`
- Error pattern: wrap API errors as `APIError`, domain errors are module-level decisions
- Benchmark utilities are internal to the module (not in core or tests)
- 200-line file limit — decompose into `image_encoding.py` etc. if needed

## Impact inventory (implementation-facing)

- **Module**: `extract_text_from_image` — `nl_processing/extract_text_from_image/`
- **Interfaces**: `ImageTextExtractor` with `extract_from_path(path: str) -> str` and `extract_from_cv2(image: numpy.ndarray) -> str`
- **Data model**: Uses `ExtractedText` from core (structured output)
- **External services**: OpenAI Vision API (via `langchain-openai` `ChatOpenAI`)
- **Dependencies**: `opencv-python` (numpy), `langchain`, `langchain-openai`, `pydantic` (all project-level except opencv)
- **Test directories**: `tests/unit/extract_text_from_image/`, `tests/integration/extract_text_from_image/`, `tests/e2e/extract_text_from_image/`
