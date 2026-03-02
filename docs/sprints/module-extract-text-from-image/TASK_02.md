---
Task ID: `T2`
Title: `Implement ImageTextExtractor service with Dutch prompt and image encoding`
Sprint: `2026-03-02_module-extract-text-from-image`
Module: `extract_text_from_image`
Depends on: `T1`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Implement the core `ImageTextExtractor` class in `service.py` with `extract_from_path()` and `extract_from_cv2()` methods, the internal image-to-base64 encoding pipeline, and the Dutch extraction prompt (`prompts/nl.json`). After this task, the happy-path extraction works: an image goes in, markdown-formatted Dutch text comes out via OpenAI Vision API. Error handling (format validation, missing text, API errors) is added in T3.

## Context (contract mapping)

- Requirements: `nl_processing/extract_text_from_image/docs/prd_extract_text_from_image.md` — ETI-FR1 (extract from path), ETI-FR2 (extract from cv2), ETI-FR3 (target language), ETI-FR4 (ignore non-target), ETI-FR5 (markdown output), ETI-FR6 (preserve structure)
- Architecture: `nl_processing/extract_text_from_image/docs/architecture_extract_text_from_image.md` — "Vision API — Image as Base64", "Two Input Methods, Shared Internal Pipeline"
- Shared: `docs/planning-artifacts/architecture.md` — "Module Public Interface Pattern", "Each Module Instantiates Its Own ChatOpenAI", SFR1 (`with_structured_output`)
- Epics: `docs/planning-artifacts/epics.md` — Story 2.1

## Preconditions

- T1 completed — `__init__.py` is empty, `opencv-python` installed
- Module-core sprint complete — `core.models`, `core.exceptions`, `core.prompts` all available
- `langchain>=0.3,<1` and `langchain-openai>=0.3,<1` installed (from core sprint)

## Non-goals

- No error handling for format validation, missing target text, or API errors — that is T3
- No benchmark utilities — that is T4
- No unit tests — that is T5 (manual verification only in this task)
- No integration/e2e tests — that is T6

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `nl_processing/extract_text_from_image/service.py` (rewrite)
- `nl_processing/extract_text_from_image/image_encoding.py` (create — if service.py would exceed 200 lines)
- `nl_processing/extract_text_from_image/prompts/nl.json` (create)
- `nl_processing/extract_text_from_image/prompts/` directory (create)

**FORBIDDEN — this task must NEVER touch:**
- `nl_processing/core/` (owned by module-core sprint)
- `nl_processing/extract_text_from_image/__init__.py` (already empty from T1)
- Any other module's code or tests
- `tests/` (tests are T5 and T6)
- `pyproject.toml` (opencv already added in T1)
- Any docs outside `docs/sprints/module-extract-text-from-image/`

**Test scope:**
- No automated tests in this task
- Manual verification: `doppler run -- uv run python -c "from nl_processing.extract_text_from_image.service import ImageTextExtractor; print('import OK')"`

## Touched surface (expected files / modules)

- `nl_processing/extract_text_from_image/service.py` — rewritten from scratch
- `nl_processing/extract_text_from_image/image_encoding.py` — created (if decomposition needed)
- `nl_processing/extract_text_from_image/prompts/` — directory created
- `nl_processing/extract_text_from_image/prompts/nl.json` — created

## Dependencies and sequencing notes

- Depends on T1 (cleanup + opencv)
- T3 (error handling) and T4 (benchmarks) both depend on this task
- Must be completed before T5 (unit tests need something to test)

## Third-party / library research (mandatory for any external dependency)

- **Library**: `langchain-openai` — `ChatOpenAI`
  - **API reference**: https://python.langchain.com/api_reference/openai/chat_models/langchain_openai.chat_models.base.ChatOpenAI.html
  - **Vision API usage with LangChain**:
    ```python
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage

    llm = ChatOpenAI(model="gpt-5-mini")

    message = HumanMessage(
        content=[
            {"type": "text", "text": "Extract Dutch text from this image in markdown format."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_string}"}},
        ]
    )
    response = llm.invoke([message])
    ```
  - **Structured output binding**:
    ```python
    structured_llm = llm.with_structured_output(ExtractedText)
    result = structured_llm.invoke([message])  # Returns ExtractedText instance
    ```
  - **Known gotchas**:
    - `with_structured_output()` works with vision messages — the model extracts text AND structures the output.
    - The `model` parameter must support vision (e.g., `gpt-4o`, `gpt-4o-mini`, `gpt-5-mini`). The architecture specifies `gpt-5-mini` as default.
    - `OPENAI_API_KEY` must be set as an environment variable. `ChatOpenAI` reads it automatically from `os.environ`.
    - Base64 image data URL format: `data:image/<format>;base64,<encoded_data>`

- **Library**: `cv2` (opencv-python) — image reading and encoding
  - **Read file**: `cv2.imread(path)` → `numpy.ndarray` (BGR format)
  - **Encode to bytes**: `cv2.imencode(".png", image)` → `(success, buffer)`; `buffer.tobytes()` → bytes
  - **Known gotchas**: `cv2.imread()` returns `None` if the file doesn't exist or can't be decoded. Check for `None` before proceeding.

- **Library**: `base64` (stdlib)
  - **Encode**: `base64.b64encode(image_bytes).decode("utf-8")` → base64 string

- **Library**: `langchain_core.prompts.ChatPromptTemplate`
  - **Save/load prompt**: Used by the prompt authoring helper (T6 from core sprint) to serialize. Here we load it for the system message.
  - For this module, the prompt may be constructed inline using `ChatPromptTemplate.from_messages()` or loaded from `prompts/nl.json`. Since the Vision API requires dynamic image content in a `HumanMessage`, the prompt template may define only the system message, with the human message (including image) constructed at runtime.

## Implementation steps (developer-facing)

1. **Create `nl_processing/extract_text_from_image/prompts/` directory**.

2. **Author the Dutch extraction prompt** — create `nl_processing/extract_text_from_image/prompts/nl.json`:
   - Use the core prompt authoring helper (`nl_processing/core/scripts/prompt_author.py`) or create the JSON manually.
   - The prompt should instruct the model (in Dutch) to:
     - Extract only Dutch text from the image
     - Preserve the original document structure as markdown (headings, emphasis, line breaks)
     - Ignore text in other languages
     - Return only the extracted text, no commentary
   - Since Vision API requires the image in a `HumanMessage`, the prompt JSON should define the **system message** only. The human message (with image) is constructed at runtime.
   - Example system prompt content (in Dutch):
     ```
     Je bent een tekst-extractie assistent. Extraheer alleen de Nederlandse tekst uit het aangeboden beeld.
     Behoud de originele documentstructuur als markdown (koppen, nadruk, regelafbrekingen).
     Negeer tekst in andere talen.
     Retourneer alleen de geëxtraheerde tekst, zonder commentaar of uitleg.
     ```

3. **Create `nl_processing/extract_text_from_image/image_encoding.py`** (internal helper, not public):
   ```python
   import base64
   import pathlib

   import cv2
   import numpy


   SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


   def get_image_format(path: str) -> str:
       """Return the file extension (lowercase) for the given image path."""
       return pathlib.Path(path).suffix.lower()


   def encode_path_to_base64(path: str) -> tuple[str, str]:
       """Read an image file and return (base64_string, media_type).

       Does NOT validate format — caller is responsible for validation.
       """
       suffix = get_image_format(path)
       media_type = _suffix_to_media_type(suffix)
       with open(path, "rb") as f:
           image_bytes = f.read()
       base64_string = base64.b64encode(image_bytes).decode("utf-8")
       return base64_string, media_type


   def encode_cv2_to_base64(image: numpy.ndarray) -> tuple[str, str]:
       """Encode an OpenCV image array to base64 PNG.

       Returns (base64_string, media_type).
       """
       success, buffer = cv2.imencode(".png", image)
       if not success:
           msg = "Failed to encode image to PNG"
           raise ValueError(msg)
       base64_string = base64.b64encode(buffer.tobytes()).decode("utf-8")
       return base64_string, "image/png"


   def _suffix_to_media_type(suffix: str) -> str:
       """Convert file extension to MIME media type."""
       mapping = {
           ".png": "image/png",
           ".jpg": "image/jpeg",
           ".jpeg": "image/jpeg",
           ".gif": "image/gif",
           ".webp": "image/webp",
       }
       return mapping[suffix]
   ```

4. **Rewrite `nl_processing/extract_text_from_image/service.py`** — replace the mock function entirely:
   ```python
   import os
   import pathlib

   from langchain_core.messages import HumanMessage, SystemMessage
   from langchain_openai import ChatOpenAI

   from nl_processing.core.models import ExtractedText, Language
   from nl_processing.core.prompts import load_prompt
   from nl_processing.extract_text_from_image.image_encoding import (
       encode_cv2_to_base64,
       encode_path_to_base64,
   )

   # Resolve prompts directory relative to this file
   _PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"


   class ImageTextExtractor:
       """Extract language-specific text from images using OpenAI Vision API.

       Usage:
           extractor = ImageTextExtractor()
           text = extractor.extract_from_path("image.png")
           text = extractor.extract_from_cv2(cv2_image)
       """

       def __init__(self, *, language: Language = Language.NL, model: str = "gpt-5-mini") -> None:
           self._language = language
           prompt_path = str(_PROMPTS_DIR / f"{language.value}.json")
           self._system_prompt = load_prompt(prompt_path)
           self._llm = ChatOpenAI(
               model=model,
               api_key=os.environ["OPENAI_API_KEY"],
           ).with_structured_output(ExtractedText)

       def extract_from_path(self, path: str) -> str:
           """Extract text from image at the given file path.

           Returns markdown-formatted text in the target language.
           """
           base64_string, media_type = encode_path_to_base64(path)
           return self._extract(base64_string, media_type)

       def extract_from_cv2(self, image: "numpy.ndarray") -> str:
           """Extract text from OpenCV image array.

           Returns markdown-formatted text in the target language.
           """
           base64_string, media_type = encode_cv2_to_base64(image)
           return self._extract(base64_string, media_type)

       def _extract(self, base64_string: str, media_type: str) -> str:
           """Internal: run the extraction chain with the base64 image."""
           system_messages = self._system_prompt.format_messages()
           human_message = HumanMessage(
               content=[
                   {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{base64_string}"}},
               ]
           )
           messages = [*system_messages, human_message]
           result = self._llm.invoke(messages)
           return result.text
   ```
   **Notes:**
   - The `import numpy` is avoided at module level — the type hint uses a string literal `"numpy.ndarray"` to avoid importing numpy unless `extract_from_cv2` is called. However, `image_encoding.py` imports numpy directly (it's always needed there). Adjust based on ruff requirements — if ruff requires the actual type, import numpy.
   - `os.environ["OPENAI_API_KEY"]` — fail loudly if not set (per architecture: no `os.getenv`).
   - `load_prompt()` loads the system prompt from the module's prompt JSON.
   - `with_structured_output(ExtractedText)` ensures the response is parsed into `ExtractedText`.
   - The `_extract()` method is the shared pipeline — both public methods converge here after encoding.

5. **Verify manually** (requires Doppler for OPENAI_API_KEY):
   ```bash
   doppler run -- uv run python -c "
   from nl_processing.extract_text_from_image.service import ImageTextExtractor
   print('Import OK')
   "
   ```
   For a full test (if a test image is available):
   ```bash
   doppler run -- uv run python -c "
   from nl_processing.extract_text_from_image.service import ImageTextExtractor
   e = ImageTextExtractor()
   # result = e.extract_from_path('test_image.png')
   # print(result)
   "
   ```

6. **Run linting**: `uv run ruff format nl_processing/extract_text_from_image/ && uv run ruff check nl_processing/extract_text_from_image/`

7. **Verify file sizes**: Ensure `service.py` and `image_encoding.py` are each under 200 lines. If `service.py` is still under 200 lines without `image_encoding.py`, you may keep the encoding logic in `service.py` instead — but decomposition is recommended for clarity.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: Uses `OPENAI_API_KEY` from environment (via Doppler dev config). No production API key collision — Doppler environments are separate.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Uses `load_prompt()` from core (T5 of core sprint), uses LangChain's built-in `with_structured_output()`. No custom parsing.
- **Correct libraries only**: `langchain-openai` and `opencv-python` from `pyproject.toml`.
- **Correct file locations**: `service.py` and `image_encoding.py` within `nl_processing/extract_text_from_image/` per architecture.
- **No regressions**: The mock `service.py` is completely replaced — no backward compatibility needed (zero-legacy policy).
- **Follow UX/spec**: Public interface matches architecture spec exactly.

## Error handling + correctness rules (mandatory)

- In this task (happy path only), errors propagate naturally:
  - `FileNotFoundError` if the image file doesn't exist
  - `cv2.imencode` returns `(False, ...)` → raise `ValueError`
  - LangChain/OpenAI exceptions propagate (T3 will wrap them)
- Do not add broad `try/except` blocks in this task — error handling is T3's responsibility.

## Zero legacy tolerance rule (mandatory)

After this task:
- The mock `service.py` (function `extract_text_from_image`) is completely replaced by the `ImageTextExtractor` class
- No backward-compatible wrapper for the old function — callers must update imports
- The old mock function is dead code — it is removed entirely

## Acceptance criteria (testable)

1. `from nl_processing.extract_text_from_image.service import ImageTextExtractor` succeeds
2. `ImageTextExtractor()` can be instantiated (with default args)
3. `ImageTextExtractor(language=Language.NL, model="gpt-5-mini")` works
4. `nl_processing/extract_text_from_image/prompts/nl.json` exists and is valid ChatPromptTemplate JSON
5. `service.py` contains `extract_from_path` and `extract_from_cv2` methods
6. `image_encoding.py` contains `encode_path_to_base64` and `encode_cv2_to_base64` functions
7. `uv run ruff check nl_processing/extract_text_from_image/` passes
8. All files are under 200 lines
9. No reference to the old mock function `extract_text_from_image` remains in `service.py`

## Verification / quality gates

- [ ] Linters/formatters pass for all module source files
- [ ] No new warnings introduced
- [ ] File sizes under 200 lines
- [ ] Manual import verification succeeds

## Edge cases

- The `numpy.ndarray` type hint in `extract_from_cv2` — use a string literal `"numpy.ndarray"` if importing numpy at module level causes issues, or import it directly. Either way, ensure ruff ANN rules pass.
- If `load_prompt()` requires `allow_dangerous_deserialization`, update the call. Test by loading the prompt manually.
- The system prompt format in `nl.json` must match what `load_prompt()` expects (LangChain ChatPromptTemplate native serialization). Verify by authoring via `prompt_author.py` or manually constructing valid JSON.

## Rollout / rollback (if relevant)

- Rollout: Replace `service.py`, create new files in a single commit.
- Rollback: Revert to previous `service.py` (mock function) via git.

## Notes / risks

- **Risk**: The Dutch prompt may not produce optimal extraction quality on the first attempt. **Mitigation**: Integration tests (T6) will validate accuracy. Prompt can be iterated.
- **Risk**: `gpt-5-mini` may not exist yet or may have a different name. **Mitigation**: The architecture specifies it as the default model. If the model name is wrong, change the default in the constructor. This is a single-line change.
- **Risk**: `with_structured_output()` combined with vision messages may behave differently than with text-only messages. **Mitigation**: This is a documented LangChain feature. Integration tests (T6) will validate end-to-end behavior.
