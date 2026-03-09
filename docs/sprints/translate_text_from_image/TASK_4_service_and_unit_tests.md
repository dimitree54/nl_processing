---
Task ID: T4
Title: Implement `ImageTextTranslator` service + unit tests
Sprint: `translate_text_from_image`
Module: `translate_text_from_image`
Depends on: T3
Parallelizable: yes, with T5
Owner: Developer
Status: planned
---

## Goal / value

Implement the core `ImageTextTranslator` service class with `translate_from_path()` and `translate_from_cv2()` methods, plus comprehensive unit tests. After this task, the service is functionally complete (pending prompt assets from T5 for live API usage).

## Context (contract mapping)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md` — FR-1 through FR-10, BR-1, DEC-1, DEC-2, DEC-6, DEC-7
- Service pattern: `packages/extract_text_from_image/src/.../service.py` (image handling) + `packages/translate_text/src/.../service.py` (translation chain)
- Error handling: `packages/core/src/nl_processing/core/exceptions.py` — `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`

## Preconditions

- T3 completed (package scaffolding, conftest.py with mock helpers).
- T1 completed (image helpers in core).
- T2 completed (extended `build_translation_chain`).

## Non-goals

- Creating the prompt JSON file (T5 handles that).
- Integration or e2e tests (T6, T7).
- Prompt generator script (T5).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/translate_text_from_image/src/nl_processing/translate_text_from_image/service.py` — NEW
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_service.py` — NEW
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_error_handling.py` — NEW

**FORBIDDEN — this task must NEVER touch:**
- Any other package's code or tests
- Root config files (already handled in T3)

**Test scope:**
- Tests go in: `packages/translate_text_from_image/tests/unit/`
- Test command: `cd packages/translate_text_from_image && env PYTHONPATH=src:../core/src uv run pytest tests/unit -x -v`
- Note: Unit tests use mocked chains, so they don't need prompt assets.

## Touched surface (expected files / modules)

- `packages/translate_text_from_image/src/nl_processing/translate_text_from_image/service.py` (new)
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_service.py` (new)
- `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_error_handling.py` (new)

## Dependencies and sequencing notes

- Depends on T3 (scaffolding must exist).
- T5 (prompt assets) runs in parallel — the service file will reference `_PROMPTS_DIR` and the prompt file, but unit tests mock the chain so they don't need the actual prompt file.
- T6 depends on both T4 and T5 (needs service + prompt for live API calls).

## Implementation steps

### Step 1: Create `service.py`

Create `packages/translate_text_from_image/src/nl_processing/translate_text_from_image/service.py` following the combined patterns of `extract_text_from_image/service.py` and `translate_text/service.py`.

**Structure** (aim for ~80-90 lines, well under 200):

```python
import pathlib

from langchain_core.messages import HumanMessage
from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError
from nl_processing.core.image_encoding import (
    encode_cv2_to_base64,
    encode_path_to_base64,
    validate_image_format,
)
from nl_processing.core.models import Language
from nl_processing.core.prompts import build_translation_chain
import numpy
from pydantic import BaseModel

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

_SUPPORTED_PAIRS: set[tuple[str, str]] = {("nl", "ru")}


class _TranslatedImageText(BaseModel):
    text: str


class ImageTextTranslator:
    """Translate text from images in a single LLM call.

    Usage:
        translator = ImageTextTranslator(
            source_language=Language.NL,
            target_language=Language.RU,
        )
        result = await translator.translate_from_path("image.png")
        result = await translator.translate_from_cv2(cv2_image)
    """

    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        reasoning_effort: str | None = None,
        service_tier: str | None = "priority",
        temperature: float | None = 0,
    ) -> None:
        self._source_language = source_language
        self._target_language = target_language
        self._chain = build_translation_chain(
            source_language=source_language,
            target_language=target_language,
            supported_pairs=_SUPPORTED_PAIRS,
            prompts_dir=_PROMPTS_DIR,
            tool_schema=_TranslatedImageText,
            model=model,
            reasoning_effort=reasoning_effort,
            service_tier=service_tier,
            temperature=temperature,
        )

    async def translate_from_path(self, path: str) -> str:
        """Translate text from image at the given file path."""
        validate_image_format(path)
        base64_string, media_type = encode_path_to_base64(path)
        return await self._atranslate(base64_string, media_type)

    async def translate_from_cv2(self, image: "numpy.ndarray") -> str:
        """Translate text from OpenCV image array."""
        base64_string, media_type = encode_cv2_to_base64(image)
        return await self._atranslate(base64_string, media_type)

    async def _atranslate(self, base64_string: str, media_type: str) -> str:
        """Internal: run the translation chain with the base64 image."""
        human_message = HumanMessage(
            content=[
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
            ]
        )
        try:
            response = await self._chain.ainvoke({"images": [human_message]})
            result = _TranslatedImageText(**response.tool_calls[0]["args"])
        except Exception as e:
            raise APIError(str(e)) from e

        if not result.text.strip():
            msg = "No text in the target language was found in the image"
            raise TargetLanguageNotFoundError(msg)

        return result.text
```

**Key design decisions reflected:**
- Uses `build_translation_chain()` from core (DEC-2) with the new kwargs from T2.
- Uses image helpers from core (DEC-3, implemented in T1).
- Single internal `_atranslate()` method for both paths (BR-1).
- Returns only translated text (DEC-6, FR-5).
- No fallbacks (DEC-7, BR-3).
- `TargetLanguageNotFoundError` for empty results (OQ-1 resolution: reuse existing error).
- `APIError` wrapping for all chain failures (FR-10).
- `_SUPPORTED_PAIRS` for pair validation (FR-9).
- Prompt placeholder variable is `images` (matching extract_text_from_image pattern).

### Step 2: Create `test_service.py`

Create `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_service.py` (~100-120 lines):

Tests to implement:
1. `test_constructor_valid_pair` — NL→RU succeeds, stores chain.
2. `test_constructor_unsupported_pair` — RU→NL raises `ValueError`.
3. `test_constructor_custom_params` — accepts `model`, `reasoning_effort`, `service_tier`, `temperature`.
4. `test_translate_from_path_happy_path` — mocked chain, returns expected text.
5. `test_translate_from_cv2_happy_path` — mocked chain with numpy array.
6. `test_both_methods_converge_to_atranslate` — both methods invoke same chain exactly once each.
7. `test_single_chain_call_per_translation` — each translate call results in exactly one `ainvoke`.

**Pattern**: Follow `extract_text_from_image/tests/unit/.../test_extract_text_from_image.py` but adapted for translation. Use `generate_test_image` from `extract_text_from_image.benchmark` for creating test image files — but wait, that would create a dependency on `extract_text_from_image`. Instead, create test images using `cv2` directly (numpy array → `cv2.imwrite`) which only depends on `opencv-python` (already a dependency).

**IMPORTANT jscpd note**: Test logic must be substantially different from existing test files. Do NOT copy test structures verbatim from `extract_text_from_image`. The test names, assertions, and flow should be unique enough to avoid 10+ line duplicates.

### Step 3: Create `test_error_handling.py`

Create `packages/translate_text_from_image/tests/unit/translate_text_from_image/test_error_handling.py` (~80-100 lines):

Tests to implement:
1. `test_unsupported_format_raises_before_chain` — `.bmp` file raises `UnsupportedImageFormatError` before any chain call.
2. `test_empty_tool_output_raises_language_not_found` — empty text from chain raises `TargetLanguageNotFoundError`.
3. `test_whitespace_tool_output_raises_language_not_found` — whitespace-only text raises same error.
4. `test_api_error_wrapping_preserves_cause` — RuntimeError wrapped as `APIError` with `__cause__`.
5. `test_api_error_wrapping_various_exceptions` — multiple exception types all wrapped as `APIError`.
6. `test_api_error_wrapping_cv2_path` — errors from cv2 path also wrapped.

**IMPORTANT**: Write unique assertion messages and test structures. The jscpd check has `minLines: 10` — any block of 10+ identical lines across packages fails the build. Use different variable names, different assertion patterns, or different helper structures than the existing error handling tests.

### Step 4: Verify

- Run: `cd packages/translate_text_from_image && env PYTHONPATH=src:../core/src uv run pytest tests/unit -x -v`
- All unit tests must pass.
- Note: Constructor tests that actually build a chain will need `OPENAI_API_KEY` env var (even with no API call) due to `ChatOpenAI` validation. Use `monkeypatch.setenv("OPENAI_API_KEY", "test-key")`.
- Note: Constructor tests also need the prompt file to exist. Since T5 hasn't run yet, these tests need to either: (a) mock the chain construction, or (b) create a temporary prompt file. The simplest approach is to mock `build_translation_chain` for constructor tests that don't need the actual chain. But looking at the pattern in existing tests — they construct the real service and then replace `_chain` with a mock. This means the prompt file must exist. **Solution**: Create a minimal placeholder `nl_ru.json` prompt file in this task (just enough for the constructor to not fail), which T5 will overwrite with the real generated prompt. Alternatively, use `monkeypatch` to mock `load_prompt`.

**Recommended approach**: Create a minimal valid prompt fixture for tests. The constructor calls `build_translation_chain` which calls `load_prompt`. Rather than mocking, create `packages/translate_text_from_image/src/nl_processing/translate_text_from_image/prompts/nl_ru.json` with a minimal valid LangChain-serialized prompt. This can be a simple 2-message prompt. T5 will regenerate this file with the full few-shot prompt.

## Production safety constraints

- No database operations.
- No API calls in unit tests (chain is mocked).
- `OPENAI_API_KEY` is set to `"test-key"` via monkeypatch — no production credentials used.

## Anti-disaster constraints

- **Reuse before build**: Uses `build_translation_chain` from core, image helpers from core.
- **No regressions**: New package only — no existing code modified.
- **jscpd compliance**: Test code must be unique. Do not copy-paste from existing test files.

## Error handling + correctness rules

- All exceptions from chain are wrapped as `APIError` with preserved `__cause__`.
- Empty/whitespace tool output raises `TargetLanguageNotFoundError`.
- Unsupported formats raise `UnsupportedImageFormatError` before chain call.
- No empty catch blocks. No fallbacks.

## Zero legacy tolerance rule

- No legacy code. Fresh implementation following established patterns.

## Acceptance criteria (testable)

1. `service.py` exists with `ImageTextTranslator` class matching the interface contract.
2. Constructor accepts all 6 kwargs: `source_language`, `target_language`, `model`, `reasoning_effort`, `service_tier`, `temperature`.
3. `translate_from_path()` validates format, encodes, and calls `_atranslate()`.
4. `translate_from_cv2()` encodes numpy array and calls `_atranslate()`.
5. Both methods converge into single `_atranslate()` internal method.
6. `_SUPPORTED_PAIRS` contains `("nl", "ru")`.
7. Unsupported pairs raise `ValueError` at init.
8. Empty tool output raises `TargetLanguageNotFoundError`.
9. Chain failures raise `APIError` with `__cause__` preserved.
10. All unit tests pass: `test_service.py` and `test_error_handling.py`.
11. `service.py` is under 200 lines.
12. Each test file is under 200 lines.

## Verification / quality gates

- [x] Unit tests added (test_service.py, test_error_handling.py)
- [x] Linters/formatters pass
- [x] No new warnings
- [x] Negative-path tests for: unsupported format, unsupported pair, empty output, chain error
- [x] jscpd: no 10+ line duplicates with other packages

## Edge cases

- Constructor with `service_tier="priority"` (default) — should work.
- Constructor with `temperature=None` — valid, uses API default.
- `translate_from_path` with valid extension but missing file — `encode_path_to_base64` raises `FileNotFoundError`, which gets wrapped as `APIError` (happens inside `_atranslate`'s try/except). Actually, `encode_path_to_base64` is called outside the try/except. This matches the extraction pattern — file not found is NOT wrapped as `APIError`, it propagates as `FileNotFoundError`. This is correct: it's a caller error, not an API error.
  - Wait — looking at the service code more carefully, `validate_image_format` and `encode_path_to_base64` are called BEFORE `_atranslate`. The try/except in `_atranslate` only wraps the chain `ainvoke` call. So `FileNotFoundError` propagates naturally. Good.

## Notes / risks

- **Risk**: Prompt file needed for constructor tests.
  - **Mitigation**: Create minimal placeholder `nl_ru.json` or mock `build_translation_chain`. Recommended: create placeholder; T5 replaces it.
- **Risk**: jscpd flagging test structure similarities with existing packages.
  - **Mitigation**: Use distinct variable names, assertion messages, and helper patterns. The conftest.py files are excluded from jscpd.
