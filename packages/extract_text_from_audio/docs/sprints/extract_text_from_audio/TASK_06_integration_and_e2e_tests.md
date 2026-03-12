---
Task ID: `T6`
Title: `Integration tests (10-case corpus) and E2E tests (full pipeline + negative paths)`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `T5`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Deliver integration tests that exercise the full 10-case Dutch voice corpus against the real `AudioTextExtractor` service with real API calls, plus E2E tests covering the complete pipeline (path-based and bytes-based), negative paths (English-only audio, unsupported format), and a performance gate. This completes the module's test coverage across all tiers (FR-12, NFR-1, NFR-2, AC-1 through AC-5).

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — FR-12 (unit/integration/e2e without sibling imports), NFR-1 (< 10s for short clips), NFR-2 (10/10 pass), QA-1 through QA-5
- Testing strategy: module spec section 4 — unit (done in T4), integration (this task), contract (this task), e2e (this task)
- Reference: `packages/extract_text_from_image/tests/integration/` and `tests/e2e/` for structural patterns

## Preconditions

- T5 completed: 10 WAV fixtures exist in `tests/e2e/extract_text_from_audio/fixtures/`, manifest exists, benchmark helpers exist.
- T4 completed: `AudioTextExtractor` service is fully implemented and unit-tested.
- `make check` passes from `packages/extract_text_from_audio/` (unit tests all green).

## Non-goals

- Modifying the service implementation (already done in T4)
- Modifying core infrastructure (done in T1-T3)
- Adding new fixtures beyond what T5 generated (except 1 English negative-path clip)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/extract_text_from_audio/tests/integration/extract_text_from_audio/` — new integration tests
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/` — new e2e tests
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/fixtures/` — add 1 English WAV fixture for negative-path test
- `packages/extract_text_from_audio/tests/integration/__init__.py` — ensure strictly empty
- `packages/extract_text_from_audio/tests/integration/extract_text_from_audio/__init__.py` — new, strictly empty
- `packages/extract_text_from_audio/tests/conftest.py` — shared test config if needed

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Core source files
- The service implementation
- Bot code

**Test scope:**
- Tests go in: `packages/extract_text_from_audio/tests/integration/` and `packages/extract_text_from_audio/tests/e2e/`
- Test command: `make check` from `packages/extract_text_from_audio/`
- Integration and e2e tests run through `doppler run --` (for OPENAI_API_KEY)

## Touched surface (expected files / modules)

- `packages/extract_text_from_audio/tests/integration/extract_text_from_audio/__init__.py` (new, empty)
- `packages/extract_text_from_audio/tests/integration/extract_text_from_audio/test_extraction_accuracy.py` (new)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/__init__.py` (ensure empty)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/test_full_extraction.py` (new)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/fixtures/english_only.wav` (new, generated)
- `packages/extract_text_from_audio/tests/conftest.py` (new if needed)

## Dependencies and sequencing notes

- Depends on T5 for fixtures, manifest, and benchmark helpers.
- This is the final task — no other tasks depend on it.
- Integration and e2e tests make real API calls requiring `OPENAI_API_KEY` via doppler.

## Third-party / library research (mandatory for any external dependency)

### OpenAI TTS API (for generating English negative-path fixture)
- Same as T5 — use `gpt-4o-mini-tts` with `response_format="wav"` to generate one English-only clip.
- **Usage**:
  ```python
  from openai import OpenAI
  client = OpenAI()
  with client.audio.speech.with_streaming_response.create(
      model="gpt-4o-mini-tts",
      voice="coral",
      input="Remember to charge your phone before leaving tomorrow.",
      instructions="Speak clearly in English.",
      response_format="wav",
  ) as response:
      response.stream_to_file("english_only.wav")
  ```

### `pytest-asyncio`
- Already in dev dependencies (`pytest-asyncio>=1.3.0,<2`).
- All async test functions use `@pytest.mark.asyncio` decorator.
- Config in `pytest.ini`: `asyncio_default_fixture_loop_scope = function`.

## Implementation steps (developer-facing)

### Step 1: Generate English-only negative-path fixture

Generate one English-only WAV clip for negative-path testing:
- Text: `"Remember to charge your phone before leaving tomorrow."`
- Save to `tests/e2e/extract_text_from_audio/fixtures/english_only.wav`
- This can be done with a small one-off script or added to the corpus generator from T5.

### Step 2: Create integration test directory structure

```
tests/integration/extract_text_from_audio/
    __init__.py   (strictly empty)
    test_extraction_accuracy.py
```

### Step 3: Create `test_extraction_accuracy.py` (integration tests)

These tests make real API calls — NO mocking.

```python
"""Integration tests: 10-case Dutch corpus with real API calls."""

import json
import pathlib
import time

import pytest

from nl_processing.extract_text_from_audio.benchmark import evaluate_extraction
from nl_processing.extract_text_from_audio.service import AudioTextExtractor

_FIXTURES_DIR = pathlib.Path(__file__).parent.parent.parent / "e2e" / "extract_text_from_audio" / "fixtures"
_MANIFEST_PATH = (
    pathlib.Path(__file__).parent.parent.parent.parent
    / "src"
    / "nl_processing"
    / "extract_text_from_audio"
    / "corpus"
    / "manifest.json"
)
```

Test cases:

- **`test_corpus_case_XX`** (10 parametrized tests, one per manifest case): Load the WAV fixture, run `extract_from_path()`, compare with expected transcript using `evaluate_extraction()`. Assert match.

  Use `@pytest.mark.parametrize` reading case IDs from the manifest to generate 10 tests dynamically:
  ```python
  def _load_manifest() -> list[dict[str, str | bool]]:
      with _MANIFEST_PATH.open() as f:
          return json.load(f)["cases"]

  @pytest.mark.asyncio
  @pytest.mark.parametrize("case", _load_manifest(), ids=lambda c: c["id"])
  async def test_corpus_case(case: dict[str, str | bool]) -> None:
      fixture_path = str(_FIXTURES_DIR / case["filename"])
      extractor = AudioTextExtractor()
      result = await extractor.extract_from_path(fixture_path)
      assert evaluate_extraction(result, case["expected_transcript"]), (
          f"Case {case['id']} failed.\nExpected: {case['expected_transcript']}\nGot: {result}"
      )
  ```

- **`test_extraction_from_wav_bytes`**: Read one fixture as bytes, call `extract_from_wav_bytes()`, verify result matches expected transcript.

- **`test_extraction_latency`**: Time one extraction call, assert it completes in < 10 seconds (NFR-1).

### Step 4: Create e2e test directory structure

Ensure:
```
tests/e2e/extract_text_from_audio/
    __init__.py   (strictly empty)
    fixtures/
        case_01.wav ... case_10.wav   (from T5)
        english_only.wav              (from Step 1)
    test_full_extraction.py
```

### Step 5: Create `test_full_extraction.py` (e2e tests)

These tests exercise the full pipeline end-to-end with real API calls:

- **`test_full_dutch_extraction_from_path`**: Pick one fixture, run `extract_from_path()`, verify non-empty string result.

- **`test_full_dutch_extraction_from_bytes`**: Read a fixture as bytes, run `extract_from_wav_bytes()`, verify non-empty string result.

- **`test_unsupported_format_raises_error`**: Create a temp `.mp3` file, verify `UnsupportedAudioFormatError` is raised.

- **`test_english_only_raises_target_language_not_found`**: Use the `english_only.wav` fixture, run `extract_from_path()`, verify `TargetLanguageNotFoundError` is raised (FR-7, QA-3).

- **`test_invalid_wav_bytes_raises_error`**: Pass `b"not a wav file"` to `extract_from_wav_bytes()`, verify `UnsupportedAudioFormatError` is raised.

- **`test_default_model_is_realtime_mini`**: Construct `AudioTextExtractor()`, verify `extractor._model == "gpt-realtime-mini"` (QA-1).

- **`test_all_corpus_cases_pass`** (contract test): Load manifest, verify all 10 cases are present and none have `promoted_to_few_shot: true` without corresponding few-shot entries in nl.json (QA-4, QA-5). This is a structural/contract test, not an API test.

### Step 6: Create `__init__.py` files

Ensure all new `__init__.py` files are strictly empty.

### Step 7: Run `make check`

Run `make check` from `packages/extract_text_from_audio/`. This will:
1. Run ruff format + check
2. Run pylint (max-module-lines=200)
3. Run `pytest tests/unit` (without doppler)
4. Run `doppler run -- pytest tests/integration` (with env vars)
5. Run `doppler run -- pytest tests/e2e` (with env vars)

All must pass.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: API calls go to OpenAI servers only. No local ports, sockets, or file conflicts with production.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Following the exact test patterns from `extract_text_from_image` integration and e2e tests.
- **Correct libraries only**: Using `pytest`, `pytest-asyncio` already in dev dependencies.
- **Correct file locations**: Tests in `tests/integration/` and `tests/e2e/` following monorepo convention.
- **No regressions**: All new test files. No existing tests modified.

## Error handling + correctness rules (mandatory)

- Tests assert specific exception types (not generic `Exception`).
- No empty assertions or assertions on `True`/`False` without context.
- Failure messages include expected vs. actual values for debugging.
- No error silencing in test code.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove. All new test files.

## Acceptance criteria (testable)

1. All 10 corpus cases pass integration tests with real API calls.
2. `extract_from_wav_bytes()` works correctly in integration test.
3. Extraction latency < 10 seconds for a short clip (NFR-1).
4. English-only audio raises `TargetLanguageNotFoundError` (FR-7).
5. Unsupported format raises `UnsupportedAudioFormatError`.
6. Invalid WAV bytes raise `UnsupportedAudioFormatError`.
7. Contract test verifies manifest completeness and consistency with nl.json.
8. Default model is `gpt-realtime-mini` (FR-2).
9. All test files under 200 lines.
10. `make check` passes completely (unit + integration + e2e).

## Verification / quality gates

- [ ] Integration tests pass with real API calls (via doppler)
- [ ] E2E tests pass with real API calls (via doppler)
- [ ] Negative-path tests exist for English audio, unsupported format, invalid bytes
- [ ] Performance gate test (< 10s) passes
- [ ] Contract/manifest consistency test passes
- [ ] All test files under 200 lines
- [ ] Linters/formatters pass (`make check`)
- [ ] All `__init__.py` files strictly empty
- [ ] No `typing.Any`, relative imports, or banned APIs in test code

## Edge cases

- OpenAI API intermittent failures — tests should not mask these; let them propagate as test failures.
- TTS-generated audio quality variation — `evaluate_extraction()` uses normalized comparison to handle minor differences.
- English clip might occasionally contain Dutch-sounding words — the expected behavior is still `TargetLanguageNotFoundError` because the primary language is English.

## Notes / risks

- **RISK**: Integration tests depend on OpenAI API availability. If the API is down, tests will fail. This is expected — no mocking allowed in integration/e2e.
- **RISK**: 10 real API calls in integration tests may hit rate limits if run rapidly. `pytest-xdist` parallel execution may need to be limited for these tests. Mitigation: The `-n auto` flag in the Makefile may parallelize, but each test creates its own short-lived session, so rate limiting should not be an issue for 10 tests.
- **RISK**: English-only negative-path test depends on the model correctly identifying non-Dutch speech. If the model occasionally transcribes English as if it were Dutch, the test may be flaky. Mitigation: Use a clearly English-only sentence.
- After this task completes, the full `make check` pipeline should pass, marking the module as production-ready.
