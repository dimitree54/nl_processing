---
Task ID: `T2`
Title: `Create WAV validator in core with unit tests`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `T1`
Parallelizable: `yes, with T3`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Create a `core.audio_validation` module that validates WAV file paths and in-memory WAV bytes, mirroring the pattern of `core.image_encoding` for images. This provides the shared validation layer required by the audio service (FR-3, FM-1).

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — FR-3 (validate before API call), FM-1 (raise UnsupportedAudioFormatError), BR-2 (validation before session)
- Reference pattern: `packages/core/src/nl_processing/core/image_encoding.py` — `validate_image_format()`, `SUPPORTED_EXTENSIONS`
- Shared helper: IF-3 — WAV validator

## Preconditions

- T1 completed: `UnsupportedAudioFormatError` exists in `core/exceptions.py`.
- `make check` passes from `packages/extract_text_from_audio/`.

## Non-goals

- Audio format conversion (v1 is WAV-only, no conversion)
- Audio content analysis (decoding PCM, sample rate checks) — that's the API's job
- Realtime runner (T3)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/core/src/nl_processing/core/audio_validation.py` — new file
- `packages/extract_text_from_audio/tests/unit/` — unit tests for the validator

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- `core/image_encoding.py`
- `core/exceptions.py` (already done in T1)
- Bot code

**Test scope:**
- Tests go in: `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/`
- Test command: `make check` from `packages/extract_text_from_audio/`

## Touched surface (expected files / modules)

- `packages/core/src/nl_processing/core/audio_validation.py` (new)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_audio_validation.py` (new)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/__init__.py` (new, strictly empty)

## Dependencies and sequencing notes

- Depends on T1 for `UnsupportedAudioFormatError`.
- Can run in parallel with T3 (realtime runner) since they don't share files.
- T4 (service) depends on this task.

## Third-party / library research (mandatory for any external dependency)

No third-party libraries. WAV validation uses only Python stdlib:

- **`wave` module (stdlib)**: Used to validate WAV file headers and in-memory WAV bytes.
  - **Documentation**: https://docs.python.org/3/library/wave.html
  - **API**: `wave.open(file, mode='rb')` — opens a WAV file for reading. Raises `wave.Error` if the file is not a valid WAV.
  - **In-memory usage**: `wave.open(io.BytesIO(data), 'rb')` works for validating bytes.
  - **Known gotchas**: `wave.open()` only supports standard PCM WAV (not compressed WAV formats like ADPCM). This is fine for v1 scope.

## Implementation steps (developer-facing)

1. **Create `packages/core/src/nl_processing/core/audio_validation.py`** with:
   - `SUPPORTED_AUDIO_EXTENSIONS = {".wav"}` constant
   - `def get_audio_format(path: str) -> str` — returns lowercase file extension
   - `def validate_audio_format(path: str) -> None` — validates file extension is `.wav`, raises `UnsupportedAudioFormatError` if not
   - `def validate_wav_bytes(audio_bytes: bytes) -> None` — validates that bytes are a valid WAV file using `wave.open(io.BytesIO(audio_bytes))`, raises `UnsupportedAudioFormatError` if invalid

   Follow the structure of `image_encoding.py` closely. Keep the file well under 200 lines.

2. **Create `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/__init__.py`** — strictly empty.

3. **Create `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_audio_validation.py`** with unit tests:
   - `test_validate_audio_format_wav_accepted` — `.wav` extension passes
   - `test_validate_audio_format_mp3_rejected` — `.mp3` raises `UnsupportedAudioFormatError`
   - `test_validate_audio_format_various_rejected` — `.m4a`, `.ogg`, `.flac`, `.webm` all raise
   - `test_validate_audio_format_case_insensitive` — `.WAV` should pass (case-insensitive extension check)
   - `test_get_audio_format_returns_lowercase` — verify extension is lowercased
   - `test_validate_wav_bytes_valid` — construct a minimal valid WAV in memory (using `wave` module), verify it passes
   - `test_validate_wav_bytes_invalid` — pass random bytes, verify `UnsupportedAudioFormatError` is raised
   - `test_validate_wav_bytes_empty` — pass empty bytes, verify `UnsupportedAudioFormatError` is raised

   To create a minimal valid WAV for testing:
   ```python
   import io, wave, struct
   buf = io.BytesIO()
   with wave.open(buf, "wb") as wf:
       wf.setnchannels(1)
       wf.setsampwidth(2)
       wf.setframerate(24000)
       wf.writeframes(struct.pack("<h", 0) * 24000)  # 1 second of silence
   valid_wav_bytes = buf.getvalue()
   ```

4. **Run `make check`** from `packages/extract_text_from_audio/` to verify all tests pass and linting is clean.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: No shared resources. Pure library code with no I/O beyond file reads during validation.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Extending core's validation pattern (parallel to `image_encoding.py`).
- **Correct libraries only**: Using only Python stdlib (`wave`, `io`).
- **Correct file locations**: New file in `core/` following established naming conventions.
- **No regressions**: New file, no existing code modified.

## Error handling + correctness rules (mandatory)

- `validate_audio_format()` raises `UnsupportedAudioFormatError` with a descriptive message including the unsupported extension and supported extensions.
- `validate_wav_bytes()` catches `wave.Error` and `EOFError` (for truncated data) from `wave.open()` and re-raises as `UnsupportedAudioFormatError` with chained cause.
- No empty catch blocks. No silent fallbacks.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. This is a new module.

## Acceptance criteria (testable)

1. `validate_audio_format("file.wav")` passes without error.
2. `validate_audio_format("file.mp3")` raises `UnsupportedAudioFormatError`.
3. `validate_wav_bytes(valid_wav)` passes for valid WAV bytes.
4. `validate_wav_bytes(b"not a wav")` raises `UnsupportedAudioFormatError`.
5. All functions are importable from `nl_processing.core.audio_validation`.
6. `audio_validation.py` is under 200 lines.
7. `make check` passes from `packages/extract_text_from_audio/`.

## Verification / quality gates

- [ ] Unit tests cover positive and negative paths for both path validation and bytes validation
- [ ] Linters/formatters pass (`make check`)
- [ ] `audio_validation.py` under 200 lines
- [ ] No `typing.Any`, relative imports, or banned APIs used
- [ ] `UnsupportedAudioFormatError` messages are descriptive

## Edge cases

- Empty bytes input (should raise `UnsupportedAudioFormatError`, not crash)
- Truncated WAV header (should raise `UnsupportedAudioFormatError`)
- `.WAV` uppercase extension (should be accepted — case-insensitive)
- File path with no extension (should raise `UnsupportedAudioFormatError`)

## Notes / risks

- The `wave` module only handles uncompressed PCM WAV. This is intentional for v1 — compressed WAV formats are out of scope.
- The WAV bytes validator checks structural validity (valid RIFF/WAV header) but does not verify audio content quality.
