---
Task ID: `T4`
Title: `Implement AudioTextExtractor service, prompt/session asset, and unit tests`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `T2, T3`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Implement the `AudioTextExtractor` service class with `extract_from_path()` and `extract_from_wav_bytes()` methods that converge into one internal execution path using the realtime runner, create the Dutch extraction session/prompt asset (`nl.json`), and deliver comprehensive unit tests covering constructor, validation, convergence, and error wrapping.

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — FR-1 through FR-9, BR-1 through BR-4, FM-1 through FM-5
- Reference: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` — `ImageTextExtractor` pattern
- Reference: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` — prompt generation pattern

## Preconditions

- T1 completed: `UnsupportedAudioFormatError` exists, root config updated.
- T2 completed: `validate_audio_format()` and `validate_wav_bytes()` exist in `core.audio_validation`.
- T3 completed: `run_realtime_audio_session()` exists in `core.realtime_runner`.
- `make check` passes from `packages/extract_text_from_audio/`.

## Non-goals

- Test corpus generation (T5)
- Integration/e2e tests with real API calls (T6)
- Benchmark helpers (T5)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/service.py` — new file
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/` — new directory with `generate_nl_prompt.py` and `nl.json`
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_service.py` — new unit tests
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_error_handling.py` — new error tests
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/conftest.py` — test fixtures

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Core source files (already completed in T1-T3)
- Bot code

**Test scope:**
- Tests go in: `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/`
- Test command: `make check` from `packages/extract_text_from_audio/`

## Touched surface (expected files / modules)

- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/service.py` (new)
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/` (new dir)
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/generate_nl_prompt.py` (new)
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/nl.json` (new, generated)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/conftest.py` (new)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_service.py` (new)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_error_handling.py` (new)

## Dependencies and sequencing notes

- Depends on T2 (WAV validator) and T3 (realtime runner) because the service imports both.
- T5 (corpus generation) and T6 (integration/e2e tests) depend on this task.

## Third-party / library research (mandatory for any external dependency)

No new third-party libraries beyond what T1-T3 already introduced. This task uses:
- `nl_processing.core.audio_validation` (from T2)
- `nl_processing.core.realtime_runner` (from T3)
- `nl_processing.core.exceptions` (from T1)
- `nl_processing.core.models` (existing — `Language` enum)

For the prompt/session asset, the approach differs from the image module:
- The image module uses LangChain `ChatPromptTemplate` serialized to JSON via `langchain_core.load.dumpd()`.
- The audio module does NOT use LangChain. The Realtime API session is configured with plain JSON instructions, not a LangChain prompt template.
- The `nl.json` asset is a simple JSON file containing session instructions and any few-shot examples (plain text, not LangChain format).

## Implementation steps (developer-facing)

### Step 1: Create the prompt/session asset directory and generator

Create `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/` directory.

Create `generate_nl_prompt.py` — a script that generates `nl.json`. The asset format:
```json
{
  "instructions": "<Dutch extraction system instructions>",
  "few_shot_examples": []
}
```

The instructions should be in Dutch (consistent with the image module pattern) and cover:
- Extract only Dutch speech as text
- Return plain transcript text, no commentary
- Ignore non-Dutch speech
- Return empty string if no Dutch speech is detected

Example instructions (adapt from image module's SYSTEM_INSTRUCTION):
```
"Je bent een transcriptie-assistent. Transcribeer alleen de Nederlandse spraak uit de aangeboden audio. Retourneer alleen de getranscribeerde tekst, zonder commentaar of uitleg. Negeer spraak in andere talen. Als er geen Nederlandse spraak hoorbaar is, retourneer dan een lege string."
```

The `few_shot_examples` array starts empty and will be populated in T5 if failing test cases need promotion (per FR-11).

The script should:
1. Define the instructions string.
2. Write `nl.json` with `json.dump()`.
3. Be runnable via `uv run python src/nl_processing/extract_text_from_audio/prompts/generate_nl_prompt.py`.

### Step 2: Generate `nl.json`

Run the generator script to produce `nl.json`. Commit the generated file as a versioned asset.

### Step 3: Create `service.py`

Create `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/service.py`:

```python
"""AudioTextExtractor — Dutch audio-to-text transcription via gpt-realtime-mini."""

import json
import pathlib

from nl_processing.core.audio_validation import validate_audio_format, validate_wav_bytes
from nl_processing.core.exceptions import APIError, TargetLanguageNotFoundError
from nl_processing.core.models import Language
from nl_processing.core.realtime_runner import run_realtime_audio_session

_PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"
_SUPPORTED_LANGUAGES = {Language.NL}


class AudioTextExtractor:
    """Extract text from Dutch audio using OpenAI Realtime API.

    Usage:
        extractor = AudioTextExtractor()
        text = await extractor.extract_from_path("audio.wav")
        text = await extractor.extract_from_wav_bytes(wav_bytes)
    """

    def __init__(
        self,
        *,
        language: Language = Language.NL,
        model: str = "gpt-realtime-mini",
    ) -> None:
        if language not in _SUPPORTED_LANGUAGES:
            msg = f"Unsupported language: {language.value}. Supported: {sorted(lang.value for lang in _SUPPORTED_LANGUAGES)}"
            raise ValueError(msg)

        self._language = language
        self._model = model

        asset_path = _PROMPTS_DIR / f"{language.value}.json"
        if not asset_path.exists():
            raise FileNotFoundError(f"Session asset not found: {asset_path}")

        with asset_path.open("r", encoding="utf-8") as f:
            asset = json.load(f)

        if not isinstance(asset, dict):
            raise TypeError(f"Session asset must be a JSON object, got {type(asset).__name__}")

        self._instructions: str = asset["instructions"]

    async def extract_from_path(self, path: str) -> str:
        """Extract Dutch text from audio at the given WAV file path."""
        validate_audio_format(path)
        with open(path, "rb") as f:
            audio_bytes = f.read()
        return await self._extract(audio_bytes)

    async def extract_from_wav_bytes(self, audio_bytes: bytes) -> str:
        """Extract Dutch text from in-memory WAV bytes."""
        validate_wav_bytes(audio_bytes)
        return await self._extract(audio_bytes)

    async def _extract(self, audio_bytes: bytes) -> str:
        """Internal: run the realtime session and return transcript text."""
        try:
            text = await run_realtime_audio_session(
                audio_bytes=audio_bytes,
                instructions=self._instructions,
                model=self._model,
            )
        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(str(e)) from e

        if not text.strip():
            msg = "No Dutch speech was found in the audio"
            raise TargetLanguageNotFoundError(msg)

        return text
```

Key design decisions:
- **Single internal path** (FR-4, BR-3): Both `extract_from_path()` and `extract_from_wav_bytes()` call `self._extract()`.
- **Validation before API** (FR-3, BR-2): `validate_audio_format()` for path, `validate_wav_bytes()` for bytes.
- **Fail-fast construction** (FR-8, FM-2, FM-4): Language validation, asset loading, and asset validation all happen in `__init__`.
- **Error wrapping** (FR-9, FM-5): Transport/parsing errors wrapped as `APIError`. Already-`APIError` exceptions are re-raised directly.
- **TargetLanguageNotFoundError** (FR-7, FM-3): Empty/whitespace-only text raises this exception.
- **No model swap** (BR-1): Model is a constructor parameter, not dynamically changed.

### Step 4: Create unit test conftest

Create `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/conftest.py`:

Provide an async mock for `run_realtime_audio_session` that can be used by monkeypatch:

```python
"""Test fixtures for extract_text_from_audio unit tests."""


class RealtimeRunnerMock:
    """Mock for run_realtime_audio_session that returns a configured response."""

    def __init__(self, return_text: str) -> None:
        self.calls: list[dict[str, str | bytes]] = []
        self._return_text = return_text

    async def __call__(self, *, audio_bytes: bytes, instructions: str, model: str) -> str:
        self.calls.append({"audio_bytes": audio_bytes, "instructions": instructions, "model": model})
        return self._return_text


class RealtimeRunnerMockError:
    """Mock that raises an exception."""

    def __init__(self, exception: Exception) -> None:
        self._exception = exception

    async def __call__(self, *, audio_bytes: bytes, instructions: str, model: str) -> str:
        raise self._exception
```

### Step 5: Create `test_service.py`

Unit tests covering:
- `test_constructor_defaults` — default language is NL, model is gpt-realtime-mini
- `test_constructor_unsupported_language` — Language.RU raises ValueError
- `test_constructor_loads_asset` — instructions loaded from nl.json
- `test_constructor_missing_asset` — non-existent language raises FileNotFoundError
- `test_extract_from_path_happy_path` — monkeypatch realtime runner, create a temp valid WAV, verify result
- `test_extract_from_wav_bytes_happy_path` — monkeypatch realtime runner, pass valid WAV bytes, verify result
- `test_both_entrypoints_use_same_internal_path` — monkeypatch runner, call both methods, verify runner was called twice with same structure (FR-4)
- `test_extract_from_path_validates_format` — `.mp3` path raises `UnsupportedAudioFormatError` before runner is called
- `test_extract_from_path_reads_file` — verify the runner receives actual file bytes

### Step 6: Create `test_error_handling.py`

Error handling tests:
- `test_empty_text_raises_target_language_not_found` — runner returns `""`, verify `TargetLanguageNotFoundError`
- `test_whitespace_text_raises_target_language_not_found` — runner returns `"   \n  "`, verify `TargetLanguageNotFoundError`
- `test_api_error_wrapping_runtime_error` — runner raises `RuntimeError`, verify `APIError` with chained cause
- `test_api_error_passthrough` — runner raises `APIError`, verify it's re-raised directly (not double-wrapped)
- `test_api_error_wrapping_various_exceptions` — runner raises various exceptions (ValueError, ConnectionError), all wrapped as `APIError`

### Step 7: Run `make check`

Verify everything passes: ruff format, ruff check, pylint, pytest.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: No local resources. Unit tests use mocks, not real API calls.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses `core.audio_validation`, `core.realtime_runner`, `core.exceptions`, `core.models`.
- **Correct libraries only**: No new dependencies beyond what's already in the project.
- **Correct file locations**: Follows `extract_text_from_image` directory structure.
- **No regressions**: All new files. No existing code modified.

## Error handling + correctness rules (mandatory)

- No empty catch blocks.
- `APIError` re-raised directly (not double-wrapped).
- Non-`APIError` exceptions wrapped with chained cause.
- `TargetLanguageNotFoundError` raised for empty/whitespace transcripts.
- Fail-fast in constructor for unsupported language, missing asset, malformed asset.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.
- `__init__.py` remains strictly empty — no exports added there.

## Acceptance criteria (testable)

1. `AudioTextExtractor()` constructs successfully with default parameters.
2. `AudioTextExtractor(language=Language.RU)` raises `ValueError`.
3. `extract_from_path("file.mp3")` raises `UnsupportedAudioFormatError` before any API call.
4. `extract_from_path("file.wav")` with mocked runner returns expected text.
5. `extract_from_wav_bytes(valid_wav)` with mocked runner returns expected text.
6. Both entrypoints call the same internal `_extract()` method (verified via mock call count).
7. Empty runner response raises `TargetLanguageNotFoundError`.
8. Runner exceptions are wrapped as `APIError` with chained cause.
9. `nl.json` exists and contains valid JSON with `instructions` key.
10. `service.py` is under 200 lines.
11. `make check` passes from `packages/extract_text_from_audio/`.

## Verification / quality gates

- [ ] Unit tests cover constructor, validation, convergence, happy path, error wrapping
- [ ] `nl.json` generated and committed
- [ ] `service.py` under 200 lines
- [ ] `generate_nl_prompt.py` under 200 lines
- [ ] Linters/formatters pass (`make check`)
- [ ] No `typing.Any`, relative imports, or banned APIs
- [ ] `__init__.py` remains strictly empty
- [ ] Negative-path tests for all error scenarios

## Edge cases

- Constructor with unsupported language (should raise immediately, not on first call)
- Constructor with missing nl.json (should raise immediately)
- Runner returns whitespace-only string (should raise TargetLanguageNotFoundError)
- Runner raises APIError directly (should not be double-wrapped)

## Notes / risks

- The prompt instructions in `nl.json` may need tuning after integration tests (T6) reveal quality issues. The generator script allows re-generation.
- Few-shot examples array starts empty. Failing test cases from T5 will be promoted per FR-11.
