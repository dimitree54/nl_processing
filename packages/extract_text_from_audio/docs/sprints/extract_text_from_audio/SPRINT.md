---
Sprint ID: `2026-03-12_extract-text-from-audio`
Sprint Goal: `Implement the extract_text_from_audio module from scaffold to fully working, tested production code that passes make check.`
Sprint Type: `module`
Module: `extract_text_from_audio`
Status: `planning`
---

## Goal

Implement the `extract_text_from_audio` module end-to-end: add missing shared infrastructure to `core` (exception, WAV validator, realtime runner), build the `AudioTextExtractor` service with its prompt/session asset, generate a 10-case Dutch TTS test corpus, and deliver unit/integration/e2e tests that all pass under `make check`.

## Module Scope

### What this sprint implements
- Module: `extract_text_from_audio`
- Module spec: `packages/extract_text_from_audio/docs/module-spec.md`
- Shared infrastructure additions in `core` (audio-specific exception, WAV validator, realtime runner)

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/` — module source code
- `packages/extract_text_from_audio/tests/` — module tests
- `packages/core/src/nl_processing/core/exceptions.py` — add `UnsupportedAudioFormatError`
- `packages/core/src/nl_processing/core/audio_validation.py` — new WAV validator (new file)
- `packages/core/src/nl_processing/core/realtime_runner.py` — new realtime audio runner (new file)
- `Makefile` (root) — add `extract_text_from_audio` to `PACKAGES`
- `ruff.toml` (root) — add `packages/extract_text_from_audio/src` to `src` list

**FORBIDDEN — this sprint must NEVER touch:**
- Any other module's source code or tests (`extract_text_from_image`, `translate_text`, etc.)
- Bot code
- Any file in `core` not listed above

### Test Scope
- **Test directory**: `packages/extract_text_from_audio/tests/`
- **Test command**: `make check` (from `packages/extract_text_from_audio/`)
- **NEVER run**: full monorepo `make check` or tests from other packages

## Interface Contract

### Public interface this sprint implements

```python
class AudioTextExtractor:
    def __init__(
        self,
        *,
        language: Language = Language.NL,
        model: str = "gpt-realtime-mini",
    ) -> None: ...

    async def extract_from_path(self, path: str) -> str: ...
    async def extract_from_wav_bytes(self, audio_bytes: bytes) -> str: ...
```

## Scope

### In
- `UnsupportedAudioFormatError` exception in `core`
- WAV validator function in `core`
- Realtime audio runner (WebSocket-based) in `core`
- `AudioTextExtractor` service class
- Package-local Dutch extraction prompt/session asset (`nl.json`)
- 10-case Dutch TTS test corpus with provenance manifest
- `benchmark.py` test helpers (normalize_text, evaluate_extraction)
- Unit tests (constructor, validation, convergence, error wrapping)
- Integration tests (10-case corpus with real API calls)
- E2E tests (full pipeline, negative paths)
- Root config updates (Makefile, ruff.toml)

### Out
- Audio translation
- Non-WAV format support
- Streaming, timestamps, diarization
- Bot integration
- `translate_text_from_audio` module

## Inputs (contracts)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` (FR-1 through FR-12, BR-1 through BR-5, NFR-1 through NFR-4)
- Reference implementation: `packages/extract_text_from_image/` (service, benchmark, prompts, test patterns)
- Core infrastructure: `packages/core/src/nl_processing/core/` (exceptions, models, prompts, image_encoding as pattern)

## Change digest

- **Requirement deltas**: No changes — implementing from the approved module spec.
- **Architecture deltas**: None — this is greenfield implementation following established patterns.

## Task list (dependency-aware)

- **T1:** `TASK_01_root_config_and_core_exception.md` (depends: --) (parallel: no) — Add root config updates and UnsupportedAudioFormatError to core
- **T2:** `TASK_02_wav_validator.md` (depends: T1) (parallel: no) — Create WAV validator in core with unit tests
- **T3:** `TASK_03_realtime_runner.md` (depends: T1) (parallel: yes, with T2) — Create realtime audio runner in core
- **T4:** `TASK_04_service_and_prompt_asset.md` (depends: T2, T3) (parallel: no) — Implement AudioTextExtractor service, prompt/session asset, and unit tests
- **T5:** `TASK_05_test_corpus_and_benchmark.md` (depends: T4) (parallel: no) — Generate 10-case Dutch TTS corpus, benchmark helpers, and provenance manifest
- **T6:** `TASK_06_integration_and_e2e_tests.md` (depends: T5) (parallel: no) — Integration tests (10-case corpus) and E2E tests (full pipeline + negative paths)

## Dependency graph (DAG)

```
T1 --> T2
T1 --> T3
T2 --> T4
T3 --> T4
T4 --> T5
T5 --> T6
```

## Execution plan

### Critical path
T1 -> T3 -> T4 -> T5 -> T6

### Parallel tracks (lanes)
- **Lane A**: T1 -> T2 -> T4
- **Lane B**: T1 -> T3 -> T4

T2 and T3 can run in parallel after T1 completes.

## Production safety

The current application version is **running in production on this same machine** (different directory).

- **Production database**: NOT modified during this sprint. No database operations.
- **Shared resource isolation**: This module uses only OpenAI API calls (WebSocket for Realtime, HTTPS for TTS fixture generation). No local ports, sockets, or file paths shared with production. All test fixtures are package-local.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- `make check` passes from `packages/extract_text_from_audio/` (ruff format, ruff check, pylint max-module-lines=200, pytest unit/integration/e2e)
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches module spec exactly (FR-1)
- `__init__.py` files are strictly empty (per root ruff.toml)
- All files under 200 lines
- No `typing.Any`, `typing.cast`, relative imports, `hasattr`/`getattr`/`setattr`, `os.getenv`/`os.environ.get`, `dict.get`, `pytest.skip`/`mark.skip`/`mark.skipif`
- Zero legacy tolerance (no dead code, no deprecated paths)
- No errors are silenced (no swallowed exceptions)
- Production database untouched
- No shared local resources conflict with production instance

## Risks + mitigations

- **Risk**: Realtime audio transport is new shared infrastructure (RISK-1 from module spec).
  - **Mitigation**: Land and test the `core` realtime runner (T3) independently before the service layer (T4). Include comprehensive error handling tests.
- **Risk**: Generated TTS corpus may not perfectly match expected transcripts on first pass (RISK-2).
  - **Mitigation**: Use normalized comparison. If baseline fails, promote failing cases into few-shot examples per FR-11.
- **Risk**: WebSocket library version incompatibility or breaking changes.
  - **Mitigation**: Research and pin `websockets` library version. Include doc links in T3.

## Migration plan (if data model changes)

N/A — no data model changes.

## Rollback / recovery notes

- Revert the commits for this sprint. Core additions (`UnsupportedAudioFormatError`, `audio_validation.py`, `realtime_runner.py`) are additive and do not modify existing code.
- Remove `extract_text_from_audio` from root `Makefile` PACKAGES and `ruff.toml` src list.

## Task validation status

- Per-task validation order: `T1` -> `T2` -> `T3` -> `T4` -> `T5` -> `T6`
- Validator: self-validation against checklist
- Outcome: pending
- Notes: —

## Sources used

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md`
- Reference implementation: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/` (service.py, benchmark.py, prompts/)
- Core code: `packages/core/src/nl_processing/core/` (exceptions.py, image_encoding.py, prompts.py, models.py, ports.py)
- Root config: `Makefile`, `ruff.toml`
- OpenAI Realtime API docs: `https://platform.openai.com/docs/guides/realtime-websocket`
- OpenAI TTS docs: `https://platform.openai.com/docs/guides/text-to-speech`

## Contract summary

### What (requirements)
- `AudioTextExtractor` with `extract_from_path()` and `extract_from_wav_bytes()` (FR-1)
- Default model `gpt-realtime-mini` (FR-2)
- WAV validation before API call (FR-3)
- Single internal execution path (FR-4)
- Plain Dutch transcript text output (FR-5)
- `TargetLanguageNotFoundError` for non-Dutch audio (FR-7)
- `UnsupportedAudioFormatError` for non-WAV input (FM-1)
- `APIError` wrapping for transport/parsing failures (FR-9)
- 10 Dutch test clips with expected outputs (FR-10)

### How (architecture)
- WebSocket-based `gpt-realtime-mini` session via new `core.realtime_runner`
- Package-local `nl.json` session/prompt asset
- Pattern follows `extract_text_from_image` service structure
- WAV validator in `core.audio_validation` (parallel to `core.image_encoding`)

## Impact inventory (implementation-facing)

- **Module**: `extract_text_from_audio` at `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/`
- **Interfaces**: `AudioTextExtractor.extract_from_path()`, `AudioTextExtractor.extract_from_wav_bytes()`
- **Data model**: No persistent data
- **External services**: OpenAI Realtime API (`gpt-realtime-mini`), OpenAI TTS API (`gpt-4o-mini-tts` for fixture generation only)
- **Test directory**: `packages/extract_text_from_audio/tests/`
