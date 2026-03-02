---
Task ID: `T3`
Title: `Implement error handling: format validation, TargetLanguageNotFoundError, APIError wrapping`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T2`
Parallelizable: `yes, with T4`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Add comprehensive error handling to the `ImageTextExtractor` service: (1) image format validation before API call — raise `UnsupportedImageFormatError` for formats not supported by OpenAI Vision API, (2) raise `TargetLanguageNotFoundError` when no text in the target language is detected or the image contains no text, (3) wrap all upstream LangChain/OpenAI exceptions as `APIError`. After this task, every failure mode documented in the PRD is handled with typed exceptions from `core`.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — ETI-FR7 (TargetLanguageNotFoundError for no target language text), ETI-FR8 (UnsupportedImageFormatError), ETI-FR9 (TargetLanguageNotFoundError for no text at all)
- Shared requirements: `docs/planning-artifacts/prd.md` — SFR9 (wrap API errors as APIError), SFR10 (no raw exceptions leak)
- Architecture: `docs/planning-artifacts/architecture.md` — "Error Handling Pattern" (two categories: APIError wrapping + module-specific domain exceptions)
- Epics: `docs/planning-artifacts/epics.md` — Story 2.2: Error Handling & Format Validation

## Preconditions

- T2 completed — `ImageTextExtractor` with happy-path extraction works
- `service.py` and `image_encoding.py` exist with the base implementation
- Core exceptions available: `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`

## Non-goals

- No new public methods — only adding error paths to existing methods
- No benchmark utilities (T4)
- No tests (T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/extract_text_from_image/service.py` (modify — add error handling)
- `nl_processing/extract_text_from_image/image_encoding.py` (modify — add format validation)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/` (owned by module-core sprint)
- `nl_processing/extract_text_from_image/__init__.py`
- `nl_processing/extract_text_from_image/prompts/`
- Any other module's code or tests
- `tests/`
- `pyproject.toml`
- Any docs outside `docs/sprints/module-extract-text-from-image/`

**Test scope:**
- No automated tests in this task (T5 will add tests for all error paths)
- Manual verification of error paths

## Touched surface (expected files / modules)

- `nl_processing/extract_text_from_image/service.py` — modified (error handling in `_extract`, `extract_from_path`)
- `nl_processing/extract_text_from_image/image_encoding.py` — modified (format validation function)

## Dependencies and sequencing notes

- Depends on T2 (service implementation exists)
- Can run in parallel with T4 (benchmark utilities) — different files
- T5 (unit tests) depends on this task (needs all error paths to test)

## Third-party / library research (mandatory for any external dependency)

- **OpenAI Vision API — supported formats**:
  - **Documentation**: https://platform.openai.com/docs/guides/vision
  - **Supported formats**: PNG (`.png`), JPEG (`.jpg`, `.jpeg`), GIF (`.gif`, non-animated only), WebP (`.webp`)
  - **Unsupported formats**: BMP, TIFF, SVG, HEIC, and all others
  - **Validation strategy**: Check file extension before reading/encoding. This is a fast pre-check that avoids sending unsupported formats to the API.

- **LangChain exception types** that can occur during chain invocation:
  - `openai.APIError` — upstream API error (rate limit, auth, server error)
  - `openai.APIConnectionError` — network issues
  - `openai.RateLimitError` — rate limit exceeded
  - `openai.AuthenticationError` — invalid API key
  - These are all subclasses of `openai.OpenAIError`. Catching the base `Exception` and re-raising as `APIError` is the safest pattern (per architecture: `except Exception as e: raise APIError(str(e)) from e`).

## Implementation steps (developer-facing)

1. **Add format validation to `image_encoding.py`**:
   Add a function `validate_image_format(path: str) -> None` that checks the file extension against `SUPPORTED_EXTENSIONS` and raises `UnsupportedImageFormatError` if not supported:
   ```python
   from nl_processing.core.exceptions import UnsupportedImageFormatError

   def validate_image_format(path: str) -> None:
       """Validate that the image format is supported by OpenAI Vision API.

       Raises:
           UnsupportedImageFormatError: If the file extension is not in SUPPORTED_EXTENSIONS.
       """
       suffix = get_image_format(path)
       if suffix not in SUPPORTED_EXTENSIONS:
           msg = f"Unsupported image format '{suffix}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
           raise UnsupportedImageFormatError(msg)
   ```

2. **Update `extract_from_path()` in `service.py`** to validate format before encoding:
   ```python
   from nl_processing.extract_text_from_image.image_encoding import validate_image_format

   def extract_from_path(self, path: str) -> str:
       validate_image_format(path)
       base64_string, media_type = encode_path_to_base64(path)
       return self._extract(base64_string, media_type)
   ```
   Format validation happens BEFORE any file reading or API call — fail fast.

3. **Add TargetLanguageNotFoundError detection to `_extract()`**:
   After the LLM returns `ExtractedText`, check if the text field is empty or whitespace-only. If so, raise `TargetLanguageNotFoundError`:
   ```python
   from nl_processing.core.exceptions import TargetLanguageNotFoundError

   def _extract(self, base64_string: str, media_type: str) -> str:
       # ... build messages ...
       result = self._llm.invoke(messages)
       if not result.text.strip():
           msg = "No text in the target language was found in the image"
           raise TargetLanguageNotFoundError(msg)
       return result.text
   ```

4. **Add APIError wrapping to `_extract()`**:
   Wrap the chain invocation in a try/except that catches all non-module exceptions and re-raises as `APIError`:
   ```python
   from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError

   def _extract(self, base64_string: str, media_type: str) -> str:
       system_messages = self._system_prompt.format_messages()
       human_message = HumanMessage(
           content=[
               {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
           ]
       )
       messages = [*system_messages, human_message]
       try:
           result = self._llm.invoke(messages)
       except Exception as e:
           raise APIError(str(e)) from e
       if not result.text.strip():
           msg = "No text in the target language was found in the image"
           raise TargetLanguageNotFoundError(msg)
       return result.text
   ```
   **Important**: The `except Exception` catches ALL upstream exceptions (LangChain, OpenAI, network, etc.) and wraps them as `APIError`. Module-specific exceptions (`TargetLanguageNotFoundError`, `UnsupportedImageFormatError`) are raised OUTSIDE the try/except — they are not API errors.

5. **Verify file sizes** — ensure both `service.py` and `image_encoding.py` remain under 200 lines.

6. **Run linting**: `uv run ruff format nl_processing/extract_text_from_image/ && uv run ruff check nl_processing/extract_text_from_image/`

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: No new resource usage. Error handling is in-process code only.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses core exceptions — no new exception classes.
- **Correct libraries only**: No new dependencies.
- **Correct file locations**: Modifying existing files within the module.
- **No regressions**: Adding error handling to existing methods; happy path behavior unchanged.

## Error handling + correctness rules (mandatory)

- **No silenced errors**: Every upstream exception is wrapped as `APIError` — none are dropped.
- **No blanket catch that discards**: The `except Exception as e: raise APIError(str(e)) from e` pattern preserves the original exception via `__cause__`.
- **Fail fast**: Format validation happens before any file reading or API call.
- **Domain exceptions are separate**: `UnsupportedImageFormatError` and `TargetLanguageNotFoundError` are raised by module logic, not by the API error wrapper.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove — adding error paths to new code.
- Ensure the happy-path code from T2 is not broken by the additions.

## Acceptance criteria (testable)

1. `extractor.extract_from_path("image.bmp")` raises `UnsupportedImageFormatError` (no API call made)
2. `extractor.extract_from_path("image.tiff")` raises `UnsupportedImageFormatError`
3. When the LLM returns empty text, `TargetLanguageNotFoundError` is raised
4. When the LLM invocation fails (any upstream exception), `APIError` is raised with the original exception as `__cause__`
5. Supported formats (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) pass validation (no error)
6. `validate_image_format` function exists in `image_encoding.py`
7. `uv run ruff check nl_processing/extract_text_from_image/` passes
8. All files under 200 lines
9. No raw LangChain/OpenAI exceptions can leak to the caller

## Verification / quality gates

- [ ] Linters/formatters pass
- [ ] No new warnings introduced
- [ ] Error handling follows the architecture pattern exactly
- [ ] No silenced errors, no empty catch blocks

## Edge cases

- File with no extension (e.g., `image`) — should raise `UnsupportedImageFormatError` (empty suffix not in `SUPPORTED_EXTENSIONS`)
- File with uppercase extension (e.g., `.PNG`) — `get_image_format()` returns lowercase, so `.PNG` → `.png` → valid. Ensure the `lower()` call is in place.
- File with double extension (e.g., `image.backup.png`) — `pathlib.Path.suffix` returns `.png` → valid.
- `extract_from_cv2` does not need format validation — cv2 arrays are always encoded as PNG internally.
- LLM returns whitespace-only text (e.g., `"  \n  "`) — `strip()` makes it empty → `TargetLanguageNotFoundError`.

## Rollout / rollback (if relevant)

- Rollout: Modify existing files in a single commit.
- Rollback: Revert the commit — happy-path code from T2 is restored.

## Notes / risks

- **Risk**: The LLM may return non-empty text even when no target language is present (e.g., describing the image in English). **Mitigation**: The prompt instructs the model to return only target-language text. If the model ignores this, the extraction will contain wrong-language text. Integration tests (T6) will catch this. A more robust approach would check the language of the returned text, but that adds complexity — start with the simple empty-check approach.
- **Risk**: Some OpenAI exceptions may not be subclasses of `Exception` (unlikely, but possible with custom error types). **Mitigation**: `except Exception` catches all standard exceptions. Non-standard ones would be a LangChain bug.
