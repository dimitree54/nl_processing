---
title: "nl_processing.core Module Spec"
module_name: "nl_processing.core"
document_type: "module-spec"
related_docs: []
---

# Module Spec: nl_processing.core

## 1. Module Snapshot

### Summary

Shared foundational package for the `nl_processing` repository. Provides domain models (language enums, word/text Pydantic models), a domain exception hierarchy, LangChain prompt loading and translation chain construction, and image encoding utilities. All other packages in the repository depend on this package.

### Package and Documentation Location

**Python package path:**

- `packages/core/src/nl_processing/core/`

**Local module doc path:**

- `packages/core/docs/module-spec.md`

### System Context

`nl_processing.core` sits at the bottom of the dependency graph. It is consumed by every other package in the repository. It has no dependencies on sibling packages — only on third-party libraries (Pydantic, LangChain, opencv-python, NumPy).

### Existing State and Change Impact

This spec documents the current code state as of 2026-03-15. No changes are proposed.

### In Scope

- Domain enums: `Language`, `PartOfSpeech`
- Domain models: `ExtractedText`, `Word`, `WordPair`, `ScoredWordPair`
- Domain exceptions: `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError`
- Prompt infrastructure: `load_prompt`, `build_translation_chain`
- Image encoding utilities: format validation, file-to-base64, OpenCV-array-to-base64
- Prompt authoring developer script: `scripts/prompt_author.py`

### Out of Scope

- Business logic for any specific NLP pipeline (extraction, translation, scoring)
- Database access or persistence
- HTTP/API layer
- Configuration management or secret handling

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | All consumer packages pin `nl-processing-core` via local path dependency | Approved | Verified in all 9 consumer `pyproject.toml` files |
| A-2 | OpenAI is the only LLM provider; `ChatOpenAI` coupling in `build_translation_chain` is intentional | Approved | Shared infrastructure decision — all translation services use OpenAI |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | Provide `Language` enum with values `nl` and `ru` | Must | Used across all translation and extraction pipelines |
| FR-2 | Provide `PartOfSpeech` enum with 13 grammatical categories | Must | Extensible — new values can be added without breaking consumers that don't use them |
| FR-3 | Provide `ExtractedText` Pydantic model with a single `text: str` field | Must | Return type for text extraction services |
| FR-4 | Provide `Word` Pydantic model with `normalized_form`, `word_type` (PartOfSpeech), and `language` (Language) | Must | Unified model for extracted and translated words; `language` is set programmatically, not by the LLM |
| FR-5 | Provide `WordPair` model pairing source and target `Word` instances | Must | Used by translation pipelines |
| FR-6 | Provide `ScoredWordPair` model extending `WordPair` with `scores` dict and stable word IDs | Must | Used by scoring/sampling pipelines |
| FR-7 | Provide `load_prompt` to deserialize LangChain-serialized JSON files into `ChatPromptTemplate` | Must | Fail-fast on missing file, malformed JSON, non-dict JSON, or wrong LangChain type |
| FR-8 | Provide `build_translation_chain` to construct a `prompt \| llm` LangChain chain from a language pair, prompts directory, and tool schema | Must | Shared infrastructure for translation-style services |
| FR-9 | Provide image format validation against OpenAI Vision API supported formats (`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`) | Must | Used by image-based pipelines |
| FR-10 | Provide file-path-to-base64 encoding returning `(base64_string, media_type)` | Must | Caller responsible for format validation |
| FR-11 | Provide OpenCV `ndarray`-to-base64 PNG encoding returning `(base64_string, media_type)` | Must | Always encodes as PNG |
| FR-12 | Provide domain exceptions: `APIError`, `TargetLanguageNotFoundError`, `UnsupportedImageFormatError` | Must | All are direct `Exception` subclasses, mutually independent |
| FR-13 | Provide `save_prompt` / `serialize_prompt_to_json` developer utilities for prompt authoring | Must | Used via `scripts/prompt_author.py`; output consumed by `load_prompt` |

### Rules and Invariants

- BR-1: All domain exceptions are direct subclasses of `Exception` — catching one must not catch another
- BR-2: `Word.language` is set programmatically by the calling service, never by the LLM
- BR-3: `PartOfSpeech` is extensible — new values may be added without breaking consumers that don't use them
- BR-4: `load_prompt` must fail fast with specific errors: `FileNotFoundError` for missing files, `TypeError` for non-dict JSON or wrong LangChain type, `JSONDecodeError` for malformed JSON
- BR-5: `encode_path_to_base64` does not validate format — caller must call `validate_image_format` separately
- BR-6: `build_translation_chain` expects prompt files named `<source_lang>_<target_lang>.json` in the given prompts directory

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Python >=3.12 | Hard constraint | Set in `pyproject.toml` |
| NFR-2 | Compatibility | Pydantic v2 | `>=2.0,<3` | Core model layer |
| NFR-3 | Compatibility | LangChain Core | `>=0.3,<1` | Prompt infrastructure |
| NFR-4 | Compatibility | LangChain OpenAI | `>=0.3,<1` | `build_translation_chain` |
| NFR-5 | Compatibility | opencv-python | `>=4.0,<5` | Image encoding |
| NFR-6 | Code quality | Max 200 lines per module | Enforced by pylint | Signal for refactoring |
| NFR-7 | Code quality | Zero code duplication | Enforced by project static-check configuration | See `.jscpd.json` and `Makefile` |
| NFR-8 | Code quality | No test skipping | Enforced by ruff banned imports | |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `load_prompt` called with non-existent path | `FileNotFoundError` raised with path in message | Caller handles |
| FM-2 | `load_prompt` called with malformed JSON | `json.JSONDecodeError` raised | Caller handles |
| FM-3 | `load_prompt` called with non-dict JSON (e.g. string) | `TypeError` raised: "must contain a JSON object" | Caller handles |
| FM-4 | `load_prompt` loads valid LangChain object that is not `ChatPromptTemplate` | `TypeError` raised: "Expected ChatPromptTemplate, got X" | Caller handles |
| FM-5 | `validate_image_format` called with unsupported extension | `UnsupportedImageFormatError` raised listing supported formats | Caller handles |
| FM-6 | `encode_cv2_to_base64` fails to encode image | `ValueError` raised: "Failed to encode image to PNG" | Caller handles |
| FM-7 | `Word` constructed with invalid `word_type` string | Pydantic `ValidationError` raised | Caller handles |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Domain model definitions (enums and Pydantic models)
- Domain exception hierarchy
- LangChain prompt serialization/deserialization and chain construction
- Image format validation and base64 encoding
- Prompt authoring developer tooling

**Does Not Own:**

- Business logic for extraction, translation, or scoring
- Prompt content (the actual `.json` prompt files live in consumer packages)
- LLM API keys or configuration
- Database schemas or persistence
- HTTP/API routing

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python import | Outbound (consumed by) | All consumer packages | `nl_processing.core.models`: `Language`, `PartOfSpeech`, `ExtractedText`, `Word`, `WordPair`, `ScoredWordPair` | Public model API; consumers import from submodules directly |
| IF-2 | Python import | Outbound (consumed by) | Translation packages | `nl_processing.core.prompts.build_translation_chain` | Returns `RunnableSerializable`; imported from submodule directly |
| IF-3 | Python import | Outbound (consumed by) | Translation packages | `nl_processing.core.prompts.load_prompt` | Returns `ChatPromptTemplate`; imported from submodule directly |
| IF-4 | Python import | Outbound (consumed by) | Image packages | `nl_processing.core.image_encoding`: `validate_image_format`, `encode_path_to_base64`, `encode_cv2_to_base64` | Image utilities; imported from submodule directly |
| IF-5 | Python import | Outbound (consumed by) | Image packages | `nl_processing.core.exceptions.UnsupportedImageFormatError` | Exception type; imported from submodule directly |
| IF-6 | Python import | Outbound (consumed by) | All consumer packages | `nl_processing.core.exceptions`: `APIError`, `TargetLanguageNotFoundError` | Exception types; imported from submodule directly |
| IF-7 | Third-party | Inbound (depends on) | Pydantic v2 | `BaseModel` | Model definitions |
| IF-8 | Third-party | Inbound (depends on) | LangChain Core + OpenAI | `ChatPromptTemplate`, `ChatOpenAI`, `load`, `dumpd` | Prompt infrastructure |
| IF-9 | Third-party | Inbound (depends on) | OpenCV + NumPy | `cv2.imencode`, `numpy.ndarray` | Image encoding |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Domain enums | Owned | `Language`, `PartOfSpeech` value sets | Stable, extended as needed | Canonical source for all packages |
| Domain models | Owned | Pydantic model schemas | Stable, versioned with package | Schema changes affect all consumers |
| Prompt JSON files | Not owned | Serialized `ChatPromptTemplate` files | Managed by consumer packages | Core only provides load/save tooling |

This package is stateless — it defines types and pure functions only. No runtime state, caching, or side effects beyond file I/O in prompt loading/saving and image encoding.

The package-level `__init__.py` is intentionally empty. This is consistent with `ruff.toml` (`strictly-empty-init-modules = true`) and the package contract: consumers import public APIs from explicit submodules rather than from `nl_processing.core` directly.

### Processing Flow

**`load_prompt` flow:**

1. Receive file path string
2. Verify file exists → `FileNotFoundError` if not
3. Parse JSON → `JSONDecodeError` if malformed
4. Verify parsed data is a dict → `TypeError` if not
5. Deserialize via `langchain_core.load.load()`
6. Verify result is `ChatPromptTemplate` → `TypeError` if not
7. Return `ChatPromptTemplate`

**`build_translation_chain` flow:**

1. Receive language pair, prompts directory, tool schema, model config
2. Construct prompt file name as `<source>_<target>.json`
3. Load prompt via `load_prompt`
4. Construct `ChatOpenAI` with model config
5. Bind tool schema to LLM
6. Return `prompt | llm` chain

**Image encoding flow:**

1. `validate_image_format`: check file extension against `SUPPORTED_EXTENSIONS` set → `UnsupportedImageFormatError` if unsupported
2. `encode_path_to_base64`: read file bytes, base64-encode, return with media type
3. `encode_cv2_to_base64`: encode ndarray as PNG via `cv2.imencode`, base64-encode, return with `image/png` media type

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Couple `build_translation_chain` to `ChatOpenAI` | Decided | All translation services use OpenAI; abstracting the provider adds complexity with no current benefit | If a second LLM provider is needed, this function must be extended or a new builder added |
| DEC-2 | Image encoding lives in core, not in image-specific packages | Decided | Multiple image packages need the same encoding logic | Core depends on `opencv-python` and `numpy` even for non-image consumers |
| DEC-3 | Prompt files use LangChain native serialization format (`dumpd`/`load`) | Decided | Round-trip fidelity with LangChain prompt objects | Prompts are not human-editable JSON; must use `prompt_author.py` or equivalent to create them |
| DEC-4 | Domain exceptions are flat (all inherit directly from `Exception`) | Decided | Keeps exception hierarchy simple; no shared base beyond `Exception` | Cannot catch "all core errors" with a single except clause |
| DEC-5 | `encode_path_to_base64` does not validate format | Decided | Separation of concerns — validation is a distinct step | Callers must remember to validate separately |

### Consistency Rules

- CR-1: All public models use Pydantic v2 `BaseModel` — no dataclasses or attrs
- CR-2: All enums use Python `enum.Enum` — no string literals for categorical values
- CR-3: All files must stay under 200 lines (pylint enforced)
- CR-4: No code duplication; enforcement details live in `.jscpd.json` and are executed via `Makefile`
- CR-5: No test skipping — failing tests must be fixed or removed
- CR-6: No `Any` types, no `typing.cast`, no `dict.get` fallbacks, no `os.getenv` silent defaults
- CR-7: All imports are absolute — relative imports banned

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1, FR-2 | models.py enums | QA-1 (test_models.py) |
| FR-3, FR-4, FR-5, FR-6 | models.py Pydantic models | QA-1 (test_models.py) |
| FR-7 | prompts.py `load_prompt` | QA-2 (test_prompts.py) |
| FR-8 | prompts.py `build_translation_chain` | QA-3 (test_build_translation_chain.py) |
| FR-9, FR-10, FR-11 | image_encoding.py | QA-4 (test_image_encoding.py) |
| FR-12 | exceptions.py | QA-5 (test_exceptions.py) |
| FR-13 | scripts/prompt_author.py | QA-6 (no dedicated test; developer tool) |
| NFR-6 | pylint max-module-lines=200 | SC-1 |
| NFR-7 | jscpd config | SC-2 |
| NFR-8 | ruff banned imports | SC-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `make check` passes with zero failures (lint + unit tests)
- AC-2: All domain models serialize and deserialize correctly via Pydantic
- AC-3: `load_prompt` round-trips LangChain prompt objects faithfully
- AC-4: All fail-fast error paths raise specific, documented exception types

### Testing Strategy

**Framework and Constraints:**

- pytest-based test suite executed via the package `Makefile`
- Active pytest behavior and CLI options are defined in `pytest.ini` and `Makefile`
- `pytest-asyncio` is available for async tests
- No test skipping allowed (enforced by `ruff.toml`)

**Unit:**

- `test_models.py`: enum values, enum counts, model instantiation, serialization, validation errors, string coercion
- `test_prompts.py`: valid load, missing file, malformed JSON, non-dict JSON, wrong LangChain type, round-trip fidelity, empty messages, complex templates
- `test_build_translation_chain.py`: chain construction, model parameter passing, tool schema binding, missing prompt error, default temperature
- `test_image_encoding.py`: format extraction, format validation (supported/unsupported/no extension), file-to-base64 round-trip, media type mapping, OpenCV-to-base64 PNG encoding with pixel fidelity
- `test_exceptions.py`: raise/catch, message preservation, exception wrapping, type independence, empty/no-args construction

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1 through FR-6 | Unit | `test_models.py`, `test_word_pairs.py` | `make check` | Covers enums and all Pydantic models |
| QA-2 | FR-7 | Unit | `test_prompts.py` | `make check` | Covers all `load_prompt` error paths and round-trip |
| QA-3 | FR-8 | Unit | `test_build_translation_chain.py` | `make check` | Chain construction, param passing, tool binding, error path |
| QA-4 | FR-9, FR-10, FR-11 | Unit | `test_image_encoding.py` | `make check` | Format validation, base64 encoding, media types, pixel fidelity |
| QA-5 | FR-12 | Unit | `test_exceptions.py` | `make check` | Covers all exception types |
| QA-6 | FR-7 | Unit | `test_prompt_loading.py` | `make check` | Covers `load_prompt` happy path and missing-file error |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | `Makefile` lint pipeline | Enforce file size limit and project lint gates | `make check` | Any configured lint failure |
| SC-2 | `.jscpd.json` via `Makefile` | Detect code duplication | `make check` | Any configured duplication failure |
| SC-3 | `ruff.toml` via `Makefile` | Enforce coding standards, banned APIs, and formatting | `make check` | Any configured Ruff failure |
| SC-4 | `pytest.ini` plus pytest invocation in `Makefile` | Enforce package test execution contract | `make check` | Any unit-test failure |
| SC-5 | `vulture` via `Makefile` | Detect unused code | `make check` | Unused code not in whitelist |

#### Manual Verification Needed

N/A — all requirements are covered by automated unit tests and static checks.

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Schema change in core models breaks all 9 consumer packages | High — repo-wide breakage | Treat model changes as cross-cutting; verify all consumers before release |
| RISK-2 | OpenCV + NumPy dependency pulled into all consumers even if they don't use image encoding | Low — slightly heavier installs | Acceptable trade-off for shared code simplicity |

### Open Questions

N/A — this spec documents existing, stable code.

### Deferred Work

N/A — no deferred work items.
