---
title: "nl_processing.core Module Spec"
module_name: "nl_processing.core"
document_type: "module-spec"
related_docs: []
---

# Module Spec: nl_processing.core

## Spec Writing Rules

This file is the target-state public contract for `nl_processing.core`. It is responsible for defining the module's purpose, scope, externally visible behavior, public interfaces, constraints, compatibility expectations, acceptance criteria, and high-level validation needs.

The spec may describe WHAT the module must do, which public types and functions are supported, which behaviors callers can rely on, which constraints materially affect consumers, and which visible failures or edge cases are part of the contract.

The spec must not document current implementation state as justification, internal file layout, private helper inventories, processing-flow internals, test framework mechanics, CI setup, or other HOW-level design details unless they are explicit contract constraints. Internal helpers may be mentioned only to mark them as internal or non-contract when that boundary needs clarification.

## 1. Module Snapshot

### Summary

`nl_processing.core` is the shared foundational package for the repository. It owns the canonical domain enums and Pydantic models, a small flat exception set, LangChain prompt loading and translation-chain construction helpers, and image encoding utilities. Other packages depend on this package for shared types and low-level reusable helpers, while domain-specific pipeline logic stays outside this module.

### Package and Documentation Location

**Python package path:**

- `packages/core/src/nl_processing/core/`

**Local module doc path:**

- `packages/core/docs/module-spec.md`

**External references allowed:**

- `packages/core/pyproject.toml`
- `packages/core/Makefile`
- `packages/core/ruff.toml`
- `packages/core/.jscpd.json`

### System Context

`nl_processing.core` sits at the bottom of the internal package dependency graph. Consumer packages import its shared types, exceptions, prompt helpers, and image helpers, while this package depends only on third-party libraries such as Pydantic, LangChain, NumPy, and OpenCV. It does not depend on sibling `packages/*` modules.

### Existing State and Change Impact

**Baseline docs reviewed:**

- `packages/core/docs/module-spec.md`
- `packages/core/pyproject.toml`
- `packages/core/Makefile`
- `packages/core/ruff.toml`
- `packages/core/.jscpd.json`

| Area | Current Documented State | Requested Change | Impact or Refactor Scope | Safer Simpler Alternative | User Confirmation |
| --- | --- | --- | --- | --- | --- |
| Module spec structure | Previous spec documented the implementation accurately but omitted several required template sections | Rewrite the document to full `module-spec-agent` template compliance | Documentation-only change; no code, interface, or migration impact | Keep the old prose-heavy spec, but it would remain non-compliant with the skill | Confirmed |
| Module behavior | Existing code behavior is stable and already documented | No behavior change requested | None | N/A | Confirmed |

### In Scope

- `Language` and `PartOfSpeech` enums
- `ExtractedText`, `Word`, `WordPair`, and `ScoredWordPair` Pydantic models
- `APIError`, `TargetLanguageNotFoundError`, and `UnsupportedImageFormatError`
- `load_prompt` and `build_translation_chain`
- Image format validation and base64 encoding helpers
- Prompt authoring helper script in `packages/core/src/nl_processing/core/scripts/prompt_author.py`
- Package-level validation expectations for lint, duplication, and unit tests

### Out of Scope

- NLP business logic implemented by consumer packages
- Prompt content owned by consumer packages
- Database access or persistence
- HTTP or API transport concerns
- Secret management and runtime environment configuration
- Cross-package migrations beyond documenting dependencies on this package

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | All current consumer packages depend on `nl-processing-core` via local path dependency `../core` | Approved | Verified from package `pyproject.toml` files in the repository |
| A-2 | OpenAI is the only LLM provider used by current translation-style services, so `build_translation_chain` may stay coupled to `ChatOpenAI` | Approved | Matches the current implementation and repo usage |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | Provide a `Language` enum that supports Dutch and Russian through members `Language.NL` and `Language.RU`, with serialized values `nl` and `ru` | Must | Canonical language identifiers used across packages |
| FR-2 | Provide `PartOfSpeech` enum with exactly 13 current grammatical categories | Must | Additional values may be added later without changing existing values |
| FR-3 | Provide `ExtractedText` model with required field `text: str` | Must | Shared return type for text extraction flows |
| FR-4 | Provide `Word` model with required fields `normalized_form`, `word_type`, and `language` | Must | `word_type` must validate against `PartOfSpeech`; `language` must validate against `Language` |
| FR-5 | Provide `WordPair` model with required `source` and `target` `Word` values | Must | Shared translation pair schema |
| FR-6 | Provide `ScoredWordPair` model with required `pair`, `scores`, `source_word_id`, and `target_word_id` fields | Must | Shared scoring and sampling schema |
| FR-7 | Provide `load_prompt(prompt_path)` that loads LangChain-native JSON and returns `ChatPromptTemplate` | Must | Must fail fast on file, JSON, and type errors |
| FR-8 | Provide `build_translation_chain(...)` that resolves `<source>_<target>.json`, loads the prompt, binds the tool schema, and returns `prompt | llm` | Must | Shared translation-style chain builder |
| FR-9 | Provide `validate_image_format(path)` that accepts only `.png`, `.jpg`, `.jpeg`, `.gif`, and `.webp` | Must | Supported set matches current OpenAI Vision usage |
| FR-10 | Provide `encode_path_to_base64(path)` returning `(base64_string, media_type)` for supported suffix mapping | Must | Caller remains responsible for separate format validation |
| FR-11 | Provide `encode_cv2_to_base64(image)` returning PNG base64 and media type `image/png` | Must | OpenCV array helper always encodes PNG |
| FR-12 | Provide direct `Exception` subclasses `APIError`, `TargetLanguageNotFoundError`, and `UnsupportedImageFormatError` | Must | Exceptions must remain distinct and independently catchable |
| FR-13 | Provide prompt-authoring helpers `serialize_prompt_to_json` and `save_prompt` usable from `prompt_author.py` | Must | Output must be consumable by `load_prompt` |

### Rules and Invariants

- BR-1: The supported `Language` members are `Language.NL` and `Language.RU`, and their serialized values remain exactly `nl` and `ru`.
- BR-2: `PartOfSpeech` currently exposes 13 values and existing values must not be renamed.
- BR-3: `Word.language` is assigned by calling services, not by the LLM.
- BR-4: All domain exceptions inherit directly from `Exception`; catching one must not catch another.
- BR-5: `load_prompt` must surface native file access errors, `json.JSONDecodeError` for malformed JSON, and `TypeError` for non-dict JSON or non-`ChatPromptTemplate` LangChain objects.
- BR-6: `build_translation_chain` must resolve prompts strictly by `<source_lang>_<target_lang>.json` in the supplied prompts directory.
- BR-7: `build_translation_chain` must not maintain a separate supported-pairs registry; missing prompt files must fail through prompt loading.
- BR-8: `encode_path_to_base64` does not perform format validation.
- BR-9: `encode_cv2_to_base64` must raise `ValueError` if OpenCV PNG encoding fails.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Python runtime compatibility | `>=3.12` | Defined in `packages/core/pyproject.toml` |
| NFR-2 | Compatibility | Pydantic compatibility | `>=2.0,<3` | Shared model layer |
| NFR-3 | Compatibility | LangChain Core compatibility | `>=0.3,<1` | Prompt loading and runnable composition |
| NFR-4 | Compatibility | LangChain OpenAI compatibility | `>=0.3,<1` | `ChatOpenAI` integration |
| NFR-5 | Compatibility | NumPy and OpenCV compatibility | `numpy>=1.0,<3`, `opencv-python>=4.0,<5` | Image helpers |
| NFR-6 | Code quality | Python modules must stay within the repo file-size rule | `pylint --max-module-lines=200` | Enforced by `make lint` |
| NFR-7 | Code quality | Python duplication tolerance | `jscpd threshold = 0` | Enforced by `make lint` |
| NFR-8 | Code quality | Test skipping is forbidden | Ruff banned API rules reject skip helpers | Enforced by `packages/core/ruff.toml` |
| NFR-9 | Reliability | Validation must fail fast on unexpected inputs or missing files | No silent defaults or fallback behavior | Matches repo-wide engineering rules |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `load_prompt` receives a missing path | Raise native `FileNotFoundError` | Caller handles or propagates |
| FM-2 | `load_prompt` reads malformed JSON | Raise `json.JSONDecodeError` | Caller handles or propagates |
| FM-3 | `load_prompt` reads valid JSON that is not a JSON object | Raise `TypeError` with object-type message | Caller handles or propagates |
| FM-4 | `load_prompt` deserializes a LangChain object that is not `ChatPromptTemplate` | Raise `TypeError` naming the actual type | Caller handles or propagates |
| FM-5 | `build_translation_chain` resolves a prompt filename that does not exist | Raise native `FileNotFoundError` from prompt loading | Caller handles or propagates |
| FM-6 | `validate_image_format` receives unsupported or extensionless path | Raise `UnsupportedImageFormatError` listing supported formats | Caller handles or propagates |
| FM-7 | `encode_cv2_to_base64` cannot encode the image as PNG | Raise `ValueError` | Caller handles or propagates |
| FM-8 | Pydantic models receive invalid enum values or missing required fields | Raise `ValidationError` | Caller handles or propagates |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Canonical shared enums and Pydantic data models
- Flat shared exception set
- LangChain prompt loading and translation-chain builder utilities
- Image suffix validation and base64 encoding helpers
- Developer-facing prompt serialization helpers

**Does Not Own:**

- Package-specific NLP workflows
- Prompt JSON assets authored by consumer packages
- LLM credentials or env var loading
- Database schemas, persistence, or migrations
- HTTP routing, controllers, or API response formatting

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python import | Outbound | Consumer packages | `nl_processing.core.models` exports shared enums and models | Public shared schema surface |
| IF-2 | Python import | Outbound | Translation-style packages | `nl_processing.core.prompts.load_prompt` | Returns `ChatPromptTemplate` |
| IF-3 | Python import | Outbound | Translation-style packages | `nl_processing.core.prompts.build_translation_chain` | Returns `RunnableSerializable` prompt-LLM chain |
| IF-4 | Python import | Outbound | Image-processing packages | `nl_processing.core.image_encoding` helpers | Provides validation and encoding helpers |
| IF-5 | Python import | Outbound | Consumer packages | `nl_processing.core.exceptions` classes | Shared exception types |
| IF-6 | Third-party library | Inbound | Pydantic v2 | `BaseModel` validation and schema generation | Used by all models |
| IF-7 | Third-party library | Inbound | LangChain Core | `load`, `dumpd`, `ChatPromptTemplate`, `RunnableSerializable` | Prompt serialization/deserialization |
| IF-8 | Third-party library | Inbound | LangChain OpenAI | `ChatOpenAI` | Current translation-chain provider binding |
| IF-9 | Third-party library | Inbound | OpenCV and NumPy | `cv2.imencode`, `numpy.ndarray` | Image encoding implementation |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| N/A | No external module change is required for this documentation rewrite | N/A | Not needed |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| `Language` and `PartOfSpeech` | Owned | Canonical shared enum definitions | Versioned with package releases | Used across consumer packages |
| `ExtractedText`, `Word`, `WordPair`, `ScoredWordPair` | Owned | Canonical shared Pydantic schemas | Versioned with package releases | Schema changes affect consumers immediately in monorepo use |
| Prompt JSON files | Referenced | LangChain-serialized prompt assets loaded from consumer-owned directories | Lifecycle owned by consumer package | Core supplies load/save helpers only |
| Runtime process state | Not owned | No cache, singleton, or mutable package state | N/A | Module is effectively stateless apart from local file I/O and encoding work |

### Processing Flow

1. `load_prompt` opens the supplied file path and parses JSON.
2. `load_prompt` verifies the parsed value is a dict, deserializes it with LangChain, and validates the result type is `ChatPromptTemplate`.
3. `build_translation_chain` derives `<source>_<target>.json`, loads the prompt, constructs `ChatOpenAI`, binds the tool schema, and returns `prompt | llm`.
4. `validate_image_format` checks the lowercase suffix against `SUPPORTED_EXTENSIONS`.
5. `encode_path_to_base64` reads bytes, maps suffix to media type, and base64-encodes the content.
6. `encode_cv2_to_base64` encodes the array as PNG via OpenCV, then base64-encodes the PNG bytes.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `build_translation_chain` directly coupled to `ChatOpenAI` | Decided | Current repository translation flows use OpenAI only | Adding a second provider will require extending or parallelizing this helper |
| DEC-2 | Keep prompt files in LangChain native serialized JSON format | Decided | Guarantees round-trip compatibility with `load` and `dumpd` | Prompt JSON is not intended for manual editing |
| DEC-3 | Keep the exception hierarchy flat | Decided | Simpler behavior and explicit catch boundaries | There is no shared `CoreError` umbrella type |
| DEC-4 | Keep image helpers inside core rather than duplicating them in consumer packages | Decided | Shared low-level utility avoids repeated implementations | Non-image consumers still install NumPy/OpenCV dependencies |
| DEC-5 | Keep format validation separate from file-path encoding | Decided | Preserves single-purpose helpers and explicit caller responsibility | Callers must validate before encoding if suffix safety matters |

### Consistency Rules

- CR-1: Public schema types use Pydantic `BaseModel`, not dataclasses or alternative model systems.
- CR-2: Public categorical values use explicit `Enum` definitions, not loose string literals.
- CR-3: Imports remain absolute; relative imports are banned by Ruff configuration.
- CR-4: No `Any`, `typing.cast`, `dict.get`, or silent env-var fallbacks are allowed in this package.
- CR-5: `__init__.py` modules remain empty unless a documented exception is introduced, consistent with `strictly-empty-init-modules = true`.
- CR-6: Test skips are forbidden; failing tests must be fixed or removed.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1 | IF-1, CR-2 | QA-1 |
| FR-2 | IF-1, BR-2, CR-2 | QA-2 |
| FR-3 | IF-1, CR-1 | QA-3 |
| FR-4 | IF-1, BR-3, CR-1 | QA-4 |
| FR-5 | IF-1, CR-1 | QA-5 |
| FR-6 | IF-1, CR-1 | QA-6 |
| FR-7 | IF-2, BR-5, DEC-2 | QA-7 |
| FR-8 | IF-3, BR-6, BR-7, DEC-1 | QA-8 |
| FR-9 | IF-4, BR-8 | QA-9 |
| FR-10 | IF-4, DEC-5 | QA-10 |
| FR-11 | IF-4, BR-9 | QA-11 |
| FR-12 | IF-5, BR-4, DEC-3 | QA-12 |
| FR-13 | IF-2, IF-7, DEC-2 | QA-13 |
| NFR-6 | CR-3, package lint command | QA-14, SC-1 |
| NFR-7 | package lint command | QA-15, SC-4 |
| NFR-8 | CR-6, Ruff banned APIs | QA-16, SC-2 |
| NFR-9 | BR-5, BR-7, BR-9, CR-4 | QA-7, QA-8, QA-11, SC-2 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `make check` in `packages/core` completes successfully.
- AC-2: Shared enums and models validate and serialize as documented.
- AC-3: Prompt loading accepts valid LangChain prompt JSON and rejects invalid file, JSON, and type inputs with explicit failures.
- AC-4: Translation-chain construction resolves prompt filenames from language pairs, forwards model configuration, and binds the requested tool schema.
- AC-5: Image helpers accept only documented suffixes, return documented media types, and fail explicitly on unsupported formats or PNG-encoding failure.
- AC-6: Shared exceptions remain direct `Exception` subclasses and distinct catch targets.

### Testing Strategy

**Framework and Constraints:**

- Use `pytest` as configured by `packages/core/pytest.ini`.
- Run unit tests with `uv run pytest -n auto tests/unit` through `make test-unit`.
- Reuse existing direct unit-test style with no skip markers.
- Reuse static checks from `make lint`: Ruff format/check, pylint max-module-lines, vulture, and jscpd.

**Unit:**

- Validate enums, models, serialization, and validation failures in `packages/core/tests/unit/core/test_models.py` and `packages/core/tests/unit/core/test_word_pairs.py`.
- Validate exceptions in `packages/core/tests/unit/core/test_exceptions.py`.
- Validate prompt loading in `packages/core/tests/unit/core/test_prompts.py` and `packages/core/tests/unit/core/test_prompt_loading.py`.
- Validate translation-chain construction in `packages/core/tests/unit/core/test_build_translation_chain.py`.
- Validate image helpers in `packages/core/tests/unit/core/test_image_encoding.py`.

**Integration:**

- N/A for the current package scope; the package exposes pure helpers and shared schemas, and its behavior is covered at unit level.

**Contract:**

- Treat enum values, model field sets, prompt-loading return type, exception types, and image-helper return shapes as contract surfaces verified by unit tests.

**E2E or UI Workflow:**

- N/A; this package has no UI or user-facing workflow.

**Operational or Non-Functional:**

- Enforce static quality, duplication, file-size, and no-skip rules through `make lint`.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1 | Unit | `test_language_enum_values`, `test_language_enum_count`, `test_language_enum_invalid_value` | PR CI / local | Verifies current `Language` contract |
| QA-2 | FR-2 | Unit | `test_part_of_speech_enum_values`, `test_part_of_speech_enum_count`, `test_part_of_speech_enum_invalid_value`, `test_part_of_speech_from_string` | PR CI / local | Verifies 13-value enum contract |
| QA-3 | FR-3 | Unit | `test_extracted_text_instantiation`, `test_extracted_text_serialization`, `test_extracted_text_json_schema`, `test_extracted_text_missing_field` | PR CI / local | Validates `ExtractedText` |
| QA-4 | FR-4 | Unit | `test_word_instantiation`, `test_word_with_string_word_type`, `test_word_serialization`, `test_word_missing_fields`, `test_word_invalid_word_type`, `test_word_russian_language` | PR CI / local | Validates `Word` behavior |
| QA-5 | FR-5 | Unit | `test_word_pair_instantiation`, `test_word_pair_serialization` | PR CI / local | Validates `WordPair` contract |
| QA-6 | FR-6 | Unit | `test_scored_word_pair_instantiation`, `test_scored_word_pair_missing_fields` | PR CI / local | Validates `ScoredWordPair` contract |
| QA-7 | FR-7, NFR-9 | Unit | `test_load_prompt_valid_file`, `test_load_prompt_missing_file`, `test_load_prompt_malformed_json`, `test_load_prompt_not_dict`, `test_load_prompt_wrong_langchain_type`, `test_load_prompt_round_trip`, `test_load_prompt_returns_stripped_content` | PR CI / local | Covers prompt success and fail-fast paths |
| QA-8 | FR-8, NFR-9 | Unit | `test_returns_chain`, `test_constructs_correct_prompt_filename`, `test_passes_model_params`, `test_binds_tool_schema`, `test_missing_prompt_file`, `test_default_temperature` | PR CI / local | Covers filename resolution and LLM binding |
| QA-9 | FR-9 | Unit | `test_validate_image_format_accepts_supported`, `test_validate_image_format_normalizes_suffix_case`, `test_validate_image_format_rejects_unsupported`, `test_validate_image_format_rejects_no_extension`, `test_supported_extensions_contains_expected_formats` | PR CI / local | Covers supported suffix policy |
| QA-10 | FR-10 | Unit | `test_encode_path_to_base64_returns_valid_base64`, `test_encode_path_to_base64_round_trips_file_content`, `test_encode_path_to_base64_jpeg_media_type`, `test_encode_path_to_base64_maps_other_media_types` | PR CI / local | Covers file-path encoding contract |
| QA-11 | FR-11, NFR-9 | Unit | `test_encode_cv2_to_base64_returns_png`, `test_encode_cv2_to_base64_preserves_pixel_data` | PR CI / local | Failure branch exists in implementation; success path is automated |
| QA-12 | FR-12 | Unit | `test_api_error_can_be_raised_and_caught`, `test_target_language_not_found_error_can_be_raised_and_caught`, `test_unsupported_image_format_error_can_be_raised_and_caught`, `test_all_exceptions_are_subclasses_of_exception`, `test_exceptions_are_distinct_types` | PR CI / local | Covers exception hierarchy and independence |
| QA-13 | FR-13 | Unit | `test_load_prompt_round_trip` plus prompt serialization path in `prompt_author.py` contract | PR CI / local | Confirms `dumpd`/`load` compatibility |
| QA-14 | NFR-6 | Static | `uv run pylint ... --max-module-lines=200` via `make lint` | PR CI / local | Enforces file-size rule |
| QA-15 | NFR-7 | Static | `npx jscpd --config .jscpd.json --exitCode 1 src tests` via `make lint` | PR CI / local | Enforces zero duplication threshold |
| QA-16 | NFR-8 | Static | `uv run ruff check --fix src tests` using banned APIs in `ruff.toml` | PR CI / local | Rejects skip helpers and banned fallback APIs |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Pylint max-module-lines gate | Enforce repo file-size rule | Local / PR CI via `make lint` | Any Python module over 200 lines |
| SC-2 | Ruff lint rules and banned APIs | Enforce import, typing, no-skip, and no-fallback rules | Local / PR CI via `make lint` | Lint violations or banned API usage |
| SC-3 | Vulture unused-code scan | Detect dead code in `src` and `tests` | Local / PR CI via `make lint` | Unused code not covered by whitelist |
| SC-4 | JSCPD duplication gate | Enforce zero duplication tolerance | Local / PR CI via `make lint` | Duplication above threshold `0` |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| N/A | Current package requirements are covered by unit tests and static checks | N/A | `make check` result |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Shared schema changes in core can break multiple consumer packages immediately | High | Treat model and enum changes as cross-package changes and validate consumers before release |
| RISK-2 | Core carries NumPy/OpenCV dependencies for consumers that do not use image helpers | Low | Accept current trade-off unless package decomposition becomes necessary |
| RISK-3 | Provider coupling in `build_translation_chain` can become a refactor point if additional LLM vendors are introduced | Medium | Add a documented extension path only when a second provider is a real requirement |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should prompt-authoring helpers receive direct unit tests instead of relying on shared `dumpd`/`load` compatibility coverage? | Open | Future package maintenance review | Current behavior is indirectly covered, but direct tests may improve confidence |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Kept as reviewed assumption documenting current repo topology | A-1 |
| RV-2 | A-2 | Approved | Promoted into explicit architectural decision | DEC-1 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open for future package hardening work | Revisit if prompt-authoring logic becomes more complex |

### Deferred Work

- D-1: Add direct tests for `serialize_prompt_to_json` and `save_prompt` if prompt-authoring behavior expands beyond the current thin wrapper.
