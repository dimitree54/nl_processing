---
Task ID: `T5`
Title: `Generate 10-case Dutch TTS corpus, benchmark helpers, and provenance manifest`
Sprint: `2026-03-12_extract-text-from-audio`
Module: `extract_text_from_audio`
Depends on: `T4`
Parallelizable: `no`
Owner: `Developer`
Status: `planned`
---

## Goal / value

Generate 10 Dutch voice test clips using OpenAI TTS API (`gpt-4o-mini-tts`), create the provenance manifest with expected transcript outputs, implement benchmark helpers (`normalize_text`, `evaluate_extraction`), and promote any failing baseline cases into the `nl.json` few-shot asset. This delivers FR-10, FR-11, CR-2, CR-3 and NFR-2.

## Context (contract mapping)

- Requirements: `packages/extract_text_from_audio/docs/module-spec.md` — FR-10 (10 Dutch test clips with provenance), FR-11 (promote failing cases), CR-2 (manifest matches few-shot), CR-3 (generator is source of truth), NFR-2 (10/10 pass)
- Reference: `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/benchmark.py` — `normalize_text`, `evaluate_extraction`
- Reference: OpenAI TTS API — IF-5 (`gpt-4o-mini-tts`, `response_format="wav"`)

## Preconditions

- T4 completed: `AudioTextExtractor` service exists and unit tests pass.
- `make check` passes from `packages/extract_text_from_audio/`.

## Non-goals

- Integration/e2e tests against the service (T6)
- Human-recorded audio clips (deferred per OQ-2)
- Non-Dutch test clips (English negative-path clip is in T6)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/benchmark.py` — new file
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/corpus/` — new directory for generator script and manifest
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/fixtures/` — new directory for generated WAV files
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_benchmark.py` — new unit tests for benchmark helpers
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/nl.json` — update if failing cases need promotion
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/prompts/generate_nl_prompt.py` — update if few-shot examples added

**FORBIDDEN — this task must NEVER touch:**
- Any other module's code or tests
- Core source files
- Bot code

**Test scope:**
- Tests go in: `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/`
- Test command: `make check` from `packages/extract_text_from_audio/`

## Touched surface (expected files / modules)

- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/benchmark.py` (new)
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/corpus/generate_corpus.py` (new)
- `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/corpus/manifest.json` (new)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/fixtures/*.wav` (new, 10 files)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/fixtures/__init__.py` (new, empty)
- `packages/extract_text_from_audio/tests/e2e/extract_text_from_audio/__init__.py` (ensure empty)
- `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_benchmark.py` (new)

## Dependencies and sequencing notes

- Depends on T4 for the service class (needed for baseline evaluation of generated clips).
- T6 (integration/e2e tests) depends on this task for fixtures and benchmark helpers.
- The corpus generator script requires `OPENAI_API_KEY` via `doppler run --` for TTS API access.

## Third-party / library research (mandatory for any external dependency)

### OpenAI TTS API (`gpt-4o-mini-tts`)
- **Library**: `openai` Python SDK
- **Version**: Latest stable (the project already depends on it via `nl-processing-core`).
- **Documentation**: https://platform.openai.com/docs/guides/text-to-speech
- **API reference**: https://platform.openai.com/docs/api-reference/audio/createSpeech
- **Python usage for WAV generation**:
  ```python
  from openai import OpenAI

  client = OpenAI()
  with client.audio.speech.with_streaming_response.create(
      model="gpt-4o-mini-tts",
      voice="coral",
      input="Dit is een test van de Nederlandse spraak.",
      instructions="Speak clearly in standard Dutch.",
      response_format="wav",
  ) as response:
      response.stream_to_file("output.wav")
  ```
- **Supported voices**: alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar. Recommend using `coral` or `marin` for Dutch.
- **Output format**: `response_format="wav"` produces standard WAV files.
- **Known gotchas**: The `instructions` parameter is available with `gpt-4o-mini-tts` to control speaking style. Dutch is well-supported.

## Implementation steps (developer-facing)

### Step 1: Create `benchmark.py`

Create `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/benchmark.py`:

```python
"""Benchmark helpers for audio text extraction evaluation."""

import re


def normalize_text(text: str) -> str:
    """Normalize text for comparison: strip whitespace, punctuation."""
    normalized = re.sub(r"[.,;:!?\"'()\-]+", "", text)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip().lower()


def evaluate_extraction(extracted: str, ground_truth: str) -> bool:
    """Compare extracted text against ground truth after normalization."""
    return normalize_text(extracted) == normalize_text(ground_truth)
```

Matches the image module's `benchmark.py` pattern but without image-specific helpers.

### Step 2: Create unit tests for benchmark helpers

Create `packages/extract_text_from_audio/tests/unit/extract_text_from_audio/test_benchmark.py`:

- `test_normalize_text_strips_whitespace` — `"  hello  world  "` -> `"hello world"`
- `test_normalize_text_removes_punctuation` — `"Hallo, wereld!"` -> `"hallo wereld"`
- `test_normalize_text_lowercases` — `"HALLO"` -> `"hallo"`
- `test_normalize_text_collapses_spaces` — `"hallo   wereld"` -> `"hallo wereld"`
- `test_evaluate_extraction_exact_match` — same text returns True
- `test_evaluate_extraction_case_insensitive` — `"Hallo"` vs `"hallo"` returns True
- `test_evaluate_extraction_punctuation_ignored` — `"Hallo, wereld!"` vs `"hallo wereld"` returns True
- `test_evaluate_extraction_mismatch` — different text returns False

### Step 3: Create the corpus generator script

Create `packages/extract_text_from_audio/src/nl_processing/extract_text_from_audio/corpus/generate_corpus.py`:

The script generates 10 Dutch WAV clips using OpenAI TTS and writes them plus a manifest. It should:

1. Define 10 Dutch sentences as test cases, varying in:
   - Simple vocabulary ("De kat zit op de mat")
   - Numbers/dates ("Het is vandaag dinsdag twaalf maart")
   - Common phrases ("Goedemorgen, hoe gaat het met u?")
   - Multi-sentence ("Nederland is een mooi land. Het regent vaak in de herfst.")
   - Compound words ("De ziekenhuismedewerker heeft een belangrijke vergadering")
   - Articles/prepositions ("De man loopt door het park naar de winkel")
   - Questions ("Waar is het dichtstbijzijnde station?")
   - Past tense ("Gisteren heb ik een boek gelezen in de bibliotheek")
   - Formal ("Geachte heer of mevrouw, ik schrijf u deze brief")
   - Informal ("Hé, heb je zin om vanavond naar de film te gaan?")

2. For each case, call the TTS API:
   ```python
   with client.audio.speech.with_streaming_response.create(
       model="gpt-4o-mini-tts",
       voice="coral",  # or vary voices
       input=dutch_text,
       instructions="Speak clearly in standard Dutch at a natural pace.",
       response_format="wav",
   ) as response:
       response.stream_to_file(output_path)
   ```

3. Write the WAV files to `tests/e2e/extract_text_from_audio/fixtures/`.

4. Write `corpus/manifest.json` with:
   ```json
   {
     "cases": [
       {
         "id": "case_01",
         "filename": "case_01.wav",
         "source_text": "De kat zit op de mat",
         "expected_transcript": "De kat zit op de mat",
         "voice": "coral",
         "model": "gpt-4o-mini-tts",
         "promoted_to_few_shot": false
       },
       ...
     ]
   }
   ```

5. Be runnable via `doppler run -- uv run python src/nl_processing/extract_text_from_audio/corpus/generate_corpus.py`.

### Step 4: Run the corpus generator

Execute the generator script to produce the 10 WAV files and manifest. This requires `OPENAI_API_KEY` via doppler.

### Step 5: Run baseline evaluation

After generating the corpus, run a baseline evaluation loop (can be a separate script or part of the generator):
1. For each case in the manifest, run `AudioTextExtractor().extract_from_path(fixture_path)`.
2. Compare with `evaluate_extraction(result, expected_transcript)`.
3. Report pass/fail for each case.

### Step 6: Promote failing cases (if any)

Per FR-11, if any cases fail baseline:
1. Add the failing case's source text and expected transcript to `prompts/generate_nl_prompt.py`'s few-shot examples.
2. Re-generate `nl.json` with the updated few-shot examples.
3. Mark `promoted_to_few_shot: true` in the manifest for promoted cases.
4. Re-run baseline to confirm all 10 cases pass.

### Step 7: Ensure all `__init__.py` files are strictly empty

Create any new `__init__.py` files needed for new directories (all strictly empty).

### Step 8: Run `make check`

Verify all unit tests pass and linting is clean.

## Production safety constraints (mandatory)

- **Database operations**: None.
- **Resource isolation**: TTS API calls go to OpenAI servers. Generated fixtures are local to this package. No collision with production.
- **Migration preparation**: N/A.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuses the `benchmark.py` pattern from the image module.
- **Correct libraries only**: Uses `openai` SDK already in the project.
- **Correct file locations**: Fixtures in `tests/e2e/extract_text_from_audio/fixtures/`, manifest in `corpus/`.
- **No regressions**: All new files.

## Error handling + correctness rules (mandatory)

- The corpus generator should fail fast if TTS API returns an error.
- No empty catch blocks in the generator.
- Baseline evaluation failures are reported clearly, not silenced.

## Zero legacy tolerance rule (mandatory)

- No legacy code to remove.

## Acceptance criteria (testable)

1. 10 WAV files exist in `tests/e2e/extract_text_from_audio/fixtures/`.
2. `corpus/manifest.json` exists with 10 case entries, each having `id`, `filename`, `source_text`, `expected_transcript`, `voice`, `model`, `promoted_to_few_shot`.
3. `benchmark.py` exports `normalize_text()` and `evaluate_extraction()`.
4. Unit tests for benchmark helpers pass.
5. All 10 WAV files are valid WAV format (openable with `wave` module).
6. If any cases were promoted, `nl.json` contains corresponding few-shot examples and `manifest.json` reflects `promoted_to_few_shot: true`.
7. `benchmark.py` is under 200 lines.
8. `generate_corpus.py` is under 200 lines.
9. `make check` passes from `packages/extract_text_from_audio/`.

## Verification / quality gates

- [ ] 10 WAV fixtures generated and committed
- [ ] Manifest complete with all fields
- [ ] Unit tests for benchmark helpers pass
- [ ] Benchmark helpers match image module's normalized comparison approach
- [ ] Linters/formatters pass (`make check`)
- [ ] All files under 200 lines
- [ ] `__init__.py` files strictly empty

## Edge cases

- TTS API returns unexpectedly short audio (should still be valid WAV)
- Dutch text with special characters (ë, ü, etc.) — TTS should handle these
- Very long sentence may produce longer audio — keep sentences short for test purposes

## Notes / risks

- **RISK**: Generated TTS audio quality may vary across voices. Mitigation: Use `coral` or `marin` which have good quality.
- **RISK**: Baseline evaluation may fail for some cases on first pass. This is expected and handled by the promotion workflow (FR-11).
- The generated WAV files will be binary-committed to the repository. They are small (short clips, ~1-5 seconds each).
