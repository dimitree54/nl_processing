---
title: "extract_text_from_audio Module Spec"
module_name: "extract_text_from_audio"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../core/docs/module-spec.md"
  - "../../translate_text_from_audio/docs/module-spec.md"
---

# Module Spec: extract_text_from_audio

## 1. Module Snapshot

### Summary

`extract_text_from_audio` is the audio equivalent of `extract_text_from_image`. It accepts Dutch speech audio, runs one short-lived `gpt-realtime-mini` request, and returns plain Dutch transcript text. The package owns its prompt/session asset, package-local generated audio fixtures, and full regression coverage.

### System Context

The module sits at the beginning of the audio workflow and feeds downstream text modules the same way `extract_text_from_image` feeds text consumers today. It depends on `core` for shared models, exceptions, and a new realtime/audio transport layer, while `translate_text_from_audio` remains a sibling package that solves direct audio translation without depending on this package at runtime.

### In Scope

- Public async `AudioTextExtractor` service for Dutch speech transcription.
- Path-based and in-memory WAV entrypoints.
- `gpt-realtime-mini` runtime model.
- Package-local prompt/session asset for Dutch extraction.
- A package-local 10-case OpenAI-generated Dutch voice corpus.
- Unit, integration, contract, and e2e tests modeled on the image module quality bar.

### Out of Scope

- Audio translation.
- Audio output, timestamps, subtitles, diarization, or streaming UI.
- Runtime fallbacks to `/v1/audio/transcriptions`, other transcription models, or sibling modules.
- Input formats that require conversion tooling in v1.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | V1 can scope public inputs to validated WAV files and WAV bytes. | Needs Review | Keeps the first module fail-fast and dependency-light. |
| A-2 | Text-only transcript output is the right public contract for this repo. | Needs Review | Matches the rest of `nl_processing`. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `AudioTextExtractor(language, model)` with async `extract_from_path(path)` and `extract_from_wav_bytes(audio_bytes)`. | Must | Mirrors the image extractor's two-entrypoint API shape. |
| FR-2 | The default runtime model must be `gpt-realtime-mini`. | Must | Direct user requirement. |
| FR-3 | `extract_from_path(path)` must validate supported audio format before any API call. | Must | Same fail-fast rule as image modules. |
| FR-4 | Both public entrypoints must converge into one internal realtime execution path after validation. | Must | Prevents behavior drift. |
| FR-5 | The public result must be plain Dutch transcript text with no assistant chatter, timestamps, or wrapper DTOs. | Must | Keeps the output usable by downstream text modules. |
| FR-6 | Non-Dutch speech must not be transcribed as if it were Dutch. | Must | Language filtering contract. |
| FR-7 | Audio containing no Dutch speech must raise `TargetLanguageNotFoundError`. | Must | No empty-string or fallback behavior. |
| FR-8 | Unsupported languages must be rejected during service construction. | Must | Same fail-fast pattern as existing modules. |
| FR-9 | Realtime transport, response parsing, or asset-loading failures must be wrapped as `APIError`. | Must | Shared caller contract. |
| FR-10 | The package must own 10 Dutch test clips generated with OpenAI voice generation, with checked-in expected transcript outputs and a provenance manifest. | Must | Direct user requirement, made package-local. |
| FR-11 | Any generated test clip that fails baseline evaluation must be promoted into the extraction few-shot asset before release and must remain in the automated regression suite. | Must | No compromise on quality gates. |
| FR-12 | The package must ship unit, integration, contract, and e2e tests without importing sibling test suites as oracles. | Must | Preserves package isolation. |

### Rules and Invariants

- BR-1: The module must use `gpt-realtime-mini` and must not silently swap runtime models.
- BR-2: Path input validation must complete before opening a realtime session.
- BR-3: Both public entrypoints must use one internal execution path.
- BR-4: The module must not fall back to specialized transcription endpoints or other repo modules.
- BR-5: Promoted failing cases remain package-local test fixtures after promotion.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Short Dutch clips must remain interactive. | <10s on a reviewed short fixture | Same bar used in image translation planning. |
| NFR-2 | Quality | The full 10-case generated corpus must pass before release. | 10/10 pass | No known failing voice fixtures may ship. |
| NFR-3 | Maintainability | Prompt/session assets and fixture manifests must be generator-owned artifacts. | Generator output matches committed assets | No hand-edited drift. |
| NFR-4 | Dependencies | V1 must avoid heavyweight media conversion dependencies. | WAV only in public contract | Keeps the module empty-to-implement cleanly. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | Unsupported or malformed audio file is provided. | Raise `UnsupportedAudioFormatError` before any API call. | Caller must provide supported WAV input. |
| FM-2 | Unsupported language is requested. | Raise `ValueError` during initialization. | Add code, prompt asset, and tests together. |
| FM-3 | Audio contains no Dutch speech. | Raise `TargetLanguageNotFoundError`. | Caller can skip or surface the failure. |
| FM-4 | Prompt/session asset is missing or malformed. | Fail fast during service construction. | Regenerate or repair before use. |
| FM-5 | Realtime session or response parsing fails. | Raise `APIError` with chained cause. | Caller can retry or surface the failure. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Dutch audio-to-text transcription behavior.
- Package-local prompt/session asset for Dutch extraction.
- Package-local generated voice fixtures and expected transcript outputs.
- Audio extraction tests across all tiers.

**Does Not Own:**

- Audio translation.
- Audio playback or spoken output.
- Persistence, batching, diarization, or timestamping.
- The shared realtime/audio infrastructure once that lives in `core`.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await extract_from_path(path: str) -> str` | Validates WAV input first. |
| IF-2 | Python API | Inbound | Callers | `await extract_from_wav_bytes(audio_bytes: bytes) -> str` | In-memory entrypoint. |
| IF-3 | Shared helper | Inbound | `core` | `Language`, `APIError`, `TargetLanguageNotFoundError`, `UnsupportedAudioFormatError`, WAV validator, realtime runner | New shared audio layer. |
| IF-4 | Asset/API | Outbound | OpenAI Realtime API | Short-lived `gpt-realtime-mini` session with text-only final output | Runtime path. |
| IF-5 | Asset/API | Outbound | OpenAI Speech API | Fixture generator using `gpt-4o-mini-tts` and `response_format="wav"` | Test corpus generation only. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Service instance state | Owned | Target language and loaded extraction asset. | Runtime only | No persistence. |
| Prompt/session asset | Owned | `nl.json` extraction instructions and few-shot examples. | Versioned with the package | Generated asset. |
| Generated WAV fixtures | Owned | 10 Dutch voice clips for regression tests. | Versioned with the package | Package-local copies. |
| Expected transcript outputs | Owned | Reviewed Dutch transcript goldens for the 10 fixtures. | Versioned with the package | Test oracle. |
| Fixture manifest | Owned | Case IDs, source scripts, voices, expected outputs, and promotion state. | Versioned with the package | Provenance and drift control. |

### Processing Flow

1. The constructor validates the target language and loads the Dutch extraction asset.
2. `extract_from_path()` validates WAV input, reads bytes, and forwards them to the internal execution path.
3. `extract_from_wav_bytes()` validates in-memory WAV bytes and forwards them to the same path.
4. The shared realtime runner opens a short-lived `gpt-realtime-mini` session and submits the audio as one request turn.
5. The final text response is parsed into plain transcript text.
6. Blank or non-Dutch results raise `TargetLanguageNotFoundError`; transport or parsing failures raise `APIError`.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Build on a new shared realtime/audio runner in `core`. | Decided | Existing `build_translation_chain(...)` does not model realtime audio. | Audio modules need shared non-LangChain infrastructure. |
| DEC-2 | Use `gpt-realtime-mini` directly at runtime. | Decided | Direct user requirement. | No runtime fallback to other audio endpoints. |
| DEC-3 | Keep public inputs WAV-only in v1. | Decided | Clean fail-fast first slice, no hidden conversion stack. | Broader audio-format support becomes follow-up work. |
| DEC-4 | Seed quality work from 10 OpenAI-generated clips and promote failing cases into few-shot examples. | Decided | Matches the requested workflow and the repo's prompt-first quality model. | Prompt tuning and regression tests stay coupled. |

### Consistency Rules

- CR-1: Supported languages require code, prompt assets, and tests in the same change.
- CR-2: Fixture IDs in the provenance manifest must match any promoted few-shot example IDs.
- CR-3: The generator script is the source of truth for fixture metadata and prompt asset generation.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | DEC-2, BR-1, IF-4 | QA-1 |
| FR-4 | BR-3, IF-1, IF-2 | QA-2 |
| FR-7 | BR-4, IF-3 | QA-3 |
| FR-10 | IF-5, DEC-4, CR-3 | QA-4 |
| FR-11 | DEC-4, BR-5, CR-2 | QA-5 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `AudioTextExtractor` exposes path and in-memory WAV entrypoints and uses one internal realtime path.
- AC-2: The runtime model defaults to `gpt-realtime-mini` and does not silently switch to another path.
- AC-3: Dutch-absent audio raises `TargetLanguageNotFoundError`.
- AC-4: The 10 generated Dutch voice fixtures, expected outputs, and manifest are checked in and reproducible.
- AC-5: Any promoted few-shot case still remains in the regression suite and passes there.

### Testing Strategy

**Framework and Constraints:**

- Reuse package-local `pytest`, `pytest-asyncio`, and `tests/unit`, `tests/integration`, `tests/e2e`.
- Run all Python commands through `uv`.
- Keep all fixtures and expected outputs local to this package.

**Unit:**

- Constructor validation and default model wiring.
- Path and bytes entrypoint convergence.
- Unsupported WAV short-circuit before any realtime call.
- `APIError` wrapping and `TargetLanguageNotFoundError` mapping.

**Integration:**

- The full 10-case generated Dutch voice corpus.
- Normalized exact-match assertions for reviewed transcript outputs.
- Performance gate on one short baseline clip.

**Contract:**

- Prompt/session asset drift check.
- Fixture manifest drift/schema check.
- Supported-language constants aligned with shipped assets.

**E2E or UI Workflow:**

- Package-local end-to-end runs over the 10 checked-in WAV fixtures.
- Dedicated English-only negative-path coverage.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit | Default-model and no-fallback constructor test | PR CI | Guards the explicit model contract. |
| QA-2 | FR-4 | Unit | Entrypoint-convergence tests for path and bytes inputs | PR CI | Mirrors existing image service invariants. |
| QA-3 | FR-7 | Integration | English-only generated clip raises `TargetLanguageNotFoundError` | PR CI / nightly | Negative-path quality gate. |
| QA-4 | FR-10 | Contract | Fixture-manifest and generator-drift test | PR CI | Keeps generated assets reproducible. |
| QA-5 | FR-11 | Contract | Promoted-case consistency check between manifest and few-shot asset | PR CI | Prevents silent prompt/test divergence. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via `make check` | Preserve lint and packaging quality. | PR CI | Formatting, lint, dead-code, or duplication failures. |
| SC-2 | Package tests | Preserve extraction behavior across all tiers. | PR CI / nightly | Any regression in unit, integration, or e2e suites. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Realism beyond synthetic TTS | Generated speech does not fully represent human recordings. | Spot-check at least one later human-recorded Dutch clip. | Reviewer notes and follow-up issue if gaps appear. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Realtime audio transport is a new shared infrastructure slice for this repo. | First implementation may carry protocol bugs. | Land and test `core` audio helpers before service implementation. |
| RISK-2 | The generated corpus may overfit clean TTS audio. | CI quality may overstate real-world robustness. | Add degraded clips now and human audio later. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Is WAV-only input acceptable for v1? | Open | Project owner to confirm before implementation | Current plan assumes yes. |
| OQ-2 | Should one human-recorded Dutch clip be required before release? | Open | Decide during QA planning | Current spec treats it as follow-up validation. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending scope confirmation | Revisit before implementation starts. |
| RV-4 | OQ-2 | Unresolved | Remains open pending QA decision | Revisit before release criteria are finalized. |

### Deferred Work

- D-1: Add mp3, m4a, or webm support only as an explicit follow-up slice.
- D-2: Add timestamps, subtitles, or diarization only if a downstream consumer requires them.
