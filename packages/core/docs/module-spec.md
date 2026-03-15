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

`nl_processing.core` is the shared foundational package for the repository. It owns the canonical domain enums and Pydantic models, a small shared exception set with explicit runtime-vs-initialization semantics, LangChain prompt-loading and model-configuration helpers, and reusable image encoding and multimodal-message utilities. Its public helper surface includes synthetic test-image generation, synthetic image data-URL generation, human multimodal image-message construction, and generic AI tool-call message construction so consumer packages can reuse one canonical contract instead of package-local prompt helpers.

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
| Prompt helpers | `core` exposed prompt loading only | Add shared public ChatOpenAI kwarg shaping for consumer packages | Public API expansion in `nl_processing.core.prompts` | Keep service-local helpers, but that would preserve duplication | Confirmed |
| Image helpers | `core` exposed validation and encoding helpers only | Add public path-encoding alias plus public synthetic image generation and data-URL helpers | Public API expansion in `nl_processing.core.image_encoding` | Keep service-local helpers, but that would preserve duplication | Confirmed |
| AI message helpers | Consumer packages used package-local tool-call AI-message builders | Add shared public `build_tool_call_ai_message(...)` helper | Public API expansion in `nl_processing.core.prompts` | Keep service-local helpers, but that would preserve duplication | Confirmed |

### In Scope

- `Language` and `PartOfSpeech` enums
- `ExtractedText`, `Word`, `WordPair`, and `ScoredWordPair` Pydantic models
- `APIError`, `UnsupportedImageFormatError`, `TargetLanguageNotFoundInInputError`, and `UnsupportedLanguageError`
- `load_prompt`
- `ChatOpenAIKwargs` and `build_llm_kwargs(...)`
- Image format validation, base64 encoding, path-encoding, synthetic test-image generation, synthetic image data-URL generation, and multimodal image-message helpers
- Public AI tool-call message construction for prompt examples and other LangChain tool-call flows
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
| FR-8 | Provide public `ChatOpenAIKwargs` plus `build_llm_kwargs(model, service_tier, reasoning_effort, temperature)` that omit `None`-valued optional model settings | Must | Shared OpenAI chat-model configuration helper |
| FR-9 | Provide `validate_image_format(path)` that accepts only `.png`, `.jpg`, `.jpeg`, `.gif`, and `.webp` | Must | Supported set matches current OpenAI Vision usage |
| FR-10 | Provide `encode_path_to_base64(path)` and `encode_image_path(path)` returning `(base64_string, media_type)` for supported suffix mapping | Must | Path encoding helpers do not hide file errors |
| FR-11 | Provide `generate_test_image(text, output_path, *, width=800, height=200, font_scale=1.0, thickness=2) -> str` that writes a synthetic text image and returns the written path string | Must | Public shared test-image helper for consumer packages and tests |
| FR-12 | Provide `generate_test_image_data_url(text, *, width=800, height=200, font_scale=1.2, thickness=2) -> str` that returns a `data:image/png;base64,...` URL for a synthetic text image | Must | Public replacement for package-local synthetic image data-URL helpers |
| FR-13 | Provide `encode_cv2_to_base64(image)` returning PNG base64 and media type `image/png` | Must | OpenCV array helper always encodes PNG |
| FR-14 | Provide `build_image_human_message(base64_string, media_type)` that creates one multimodal `HumanMessage` with a data URL image payload | Must | Shared image request-shaping helper |
| FR-15 | Provide `build_tool_call_ai_message(tool_name, tool_args, call_id, *, content="")` that creates one `AIMessage` containing exactly one tool call with the supplied name, args, and id | Must | Shared AI-message helper must stay generic rather than package-specific |
| FR-16 | Provide `APIError`, `UnsupportedImageFormatError`, `TargetLanguageNotFoundInInputError`, and `UnsupportedLanguageError` as distinct public exception types | Must | Runtime input-validation and initialization-time language failures must be separable |
| FR-17 | Provide prompt-authoring helpers `serialize_prompt_to_json` and `save_prompt` usable from `prompt_author.py` | Must | Output must be consumable by `load_prompt` |

### Rules and Invariants

- BR-1: The supported `Language` members are `Language.NL` and `Language.RU`, and their serialized values remain exactly `nl` and `ru`.
- BR-2: `PartOfSpeech` currently exposes 13 values and existing values must not be renamed.
- BR-3: `Word.language` is assigned by calling services, not by the LLM.
- BR-4: `TargetLanguageNotFoundInInputError` must inherit from `RuntimeError` because it signals invalid runtime input for a module that is otherwise correctly configured.
- BR-5: `UnsupportedLanguageError` must inherit from `ValueError` because it signals invalid language configuration during initialization.
- BR-6: `load_prompt` must surface native file access errors, `json.JSONDecodeError` for malformed JSON, and `TypeError` for non-dict JSON or non-`ChatPromptTemplate` LangChain objects.
- BR-7: `build_llm_kwargs` must never forward optional keys whose values are `None`.
- BR-8: `encode_path_to_base64` and `encode_image_path` do not perform format validation.
- BR-9: `generate_test_image` must render each newline-delimited input line into the output image and raise `ValueError` if the image cannot be written.
- BR-10: `generate_test_image_data_url` must return a complete `data:image/png;base64,<payload>` URL and preserve `ValueError` or native file I/O failures from the helper operations it composes.
- BR-11: `encode_cv2_to_base64` must raise `ValueError` if OpenCV PNG encoding fails.
- BR-12: `build_image_human_message` must always emit exactly one `image_url` content block using a `data:<media_type>;base64,<payload>` URL.
- BR-13: `build_tool_call_ai_message` must preserve caller-supplied `tool_name`, `tool_args`, and `call_id`, emit exactly one tool call, and default `content` to the empty string.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Python runtime compatibility | `>=3.12` | Defined in `packages/core/pyproject.toml` |
| NFR-2 | Compatibility | Pydantic compatibility | `>=2.0,<3` | Shared model layer |
| NFR-3 | Compatibility | LangChain Core compatibility | `>=0.3,<1` | Prompt loading and runnable composition |
| NFR-4 | Compatibility | NumPy and OpenCV compatibility | `numpy>=1.0,<3`, `opencv-python>=4.0,<5` | Image helpers |
| NFR-5 | Code quality | Python modules must stay within the repo file-size rule | `pylint --max-module-lines=200` | Enforced by `make lint` |
| NFR-6 | Code quality | Python duplication tolerance | `jscpd threshold = 0` | Enforced by `make lint` |
| NFR-7 | Code quality | Test skipping is forbidden | Ruff banned API rules reject skip helpers | Enforced by `packages/core/ruff.toml` |
| NFR-8 | Reliability | Validation must fail fast on unexpected inputs or missing files | No silent defaults or fallback behavior | Matches repo-wide engineering rules |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `load_prompt` receives a missing path | Raise native `FileNotFoundError` | Caller handles or propagates |
| FM-2 | `load_prompt` reads malformed JSON | Raise `json.JSONDecodeError` | Caller handles or propagates |
| FM-3 | `load_prompt` reads valid JSON that is not a JSON object | Raise `TypeError` with object-type message | Caller handles or propagates |
| FM-4 | `load_prompt` deserializes a LangChain object that is not `ChatPromptTemplate` | Raise `TypeError` naming the actual type | Caller handles or propagates |
| FM-5 | `validate_image_format` receives unsupported or extensionless path | Raise `UnsupportedImageFormatError` listing supported formats | Caller handles or propagates |
| FM-6 | `encode_path_to_base64` or `encode_image_path` receives a missing path | Raise native `FileNotFoundError` | Caller handles or propagates |
| FM-7 | `generate_test_image` cannot write the output image | Raise `ValueError` | Caller handles or propagates |
| FM-8 | `generate_test_image_data_url` cannot complete temporary-image generation or PNG path encoding | Raise the underlying `ValueError` or native file I/O exception | Caller handles or propagates |
| FM-9 | `encode_cv2_to_base64` cannot encode the image as PNG | Raise `ValueError` | Caller handles or propagates |
| FM-10 | Pydantic models receive invalid enum values or missing required fields | Raise `ValidationError` | Caller handles or propagates |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Canonical shared enums and Pydantic data models
- Shared exception types with explicit runtime-vs-initialization semantics
- LangChain prompt loading, ChatOpenAI kwarg-shaping, and AI tool-call message utilities
- Image suffix validation, base64 encoding, path encoding, synthetic image generation, synthetic image data-URL generation, and multimodal image-message helpers
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
| IF-2 | Python import | Outbound | Consumer packages | `nl_processing.core.prompts.load_prompt`, `ChatOpenAIKwargs`, `build_llm_kwargs(...)`, and `build_tool_call_ai_message(...)` | Returns prompt objects plus shared chat-model and AI-message helpers |
| IF-3 | Python import | Outbound | Image-processing packages | `nl_processing.core.image_encoding` helpers | Provides validation, encoding, synthetic image generation, data-URL generation, and multimodal image-message helpers |
| IF-4 | Python import | Outbound | Consumer packages | `nl_processing.core.exceptions` classes | Shared exception types |
| IF-5 | Third-party library | Inbound | Pydantic v2 | `BaseModel` validation and schema generation | Used by all models |
| IF-6 | Third-party library | Inbound | LangChain Core | `load`, `dumpd`, `ChatPromptTemplate`, `HumanMessage`, and `AIMessage` | Prompt serialization/deserialization and message helper contracts |
| IF-7 | Third-party library | Inbound | OpenCV and NumPy | `cv2.imencode`, `numpy.ndarray` | Image encoding implementation |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| `extract_text_from_image` | The extractor consumes shared ChatOpenAI kwarg shaping, synthetic image data-URL generation, multimodal image helpers, and AI tool-call message helpers from `core` | `../../extract_text_from_image/docs/module-spec.md` | Exists |

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
3. `validate_image_format` checks the lowercase suffix against the internal `_SUPPORTED_EXTENSIONS` set.
4. `build_llm_kwargs` shapes ChatOpenAI kwargs and omits optional keys whose values are `None`.
5. `encode_path_to_base64` and `encode_image_path` read bytes, map suffix to media type, and base64-encode the content.
6. `generate_test_image` writes a synthetic image for the supplied text and returns the written path string.
7. `generate_test_image_data_url` generates a synthetic PNG image and returns a complete base64 data URL.
8. `encode_cv2_to_base64` encodes the array as PNG via OpenCV, then base64-encodes the PNG bytes.
9. `build_image_human_message` wraps the encoded payload in a one-image multimodal `HumanMessage`.
10. `build_tool_call_ai_message` wraps caller-supplied tool-call fields in a one-call `AIMessage`.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep prompt files in LangChain native serialized JSON format | Decided | Guarantees round-trip compatibility with `load` and `dumpd` | Prompt JSON is not intended for manual editing |
| DEC-2 | Keep exception roles explicit through standard-library base types | Decided | Runtime input failures and initialization-time configuration failures need different catch behavior | There is no shared `CoreError` umbrella type |
| DEC-3 | Keep image helpers inside core rather than duplicating them in consumer packages | Decided | Shared low-level utility avoids repeated implementations | Non-image consumers still install NumPy/OpenCV dependencies |
| DEC-4 | Keep ChatOpenAI kwarg shaping in core instead of service-local helpers | Decided | Shared model configuration should not be reimplemented per package | Consumer packages can adopt one fail-fast helper |
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
| FR-7 | IF-2, BR-6, DEC-1 | QA-7 |
| FR-8 | IF-2, BR-7, DEC-4 | QA-8 |
| FR-9 | IF-3, BR-8 | QA-9 |
| FR-10 | IF-3, BR-8, DEC-5 | QA-10 |
| FR-11 | IF-3, BR-9 | QA-11 |
| FR-12 | IF-3, BR-10 | QA-12 |
| FR-13 | IF-3, BR-11 | QA-13 |
| FR-14 | IF-3, BR-12 | QA-14 |
| FR-15 | IF-2, BR-13 | QA-15 |
| FR-16 | IF-4, BR-4, BR-5, DEC-2 | QA-16 |
| FR-17 | IF-2, IF-6, DEC-1 | QA-17 |
| NFR-5 | CR-3, package lint command | QA-18, SC-1 |
| NFR-6 | package lint command | QA-18, SC-4 |
| NFR-7 | CR-6, Ruff banned APIs | QA-20, SC-2 |
| NFR-8 | BR-6, BR-9, BR-10, BR-11, CR-4 | QA-7, QA-11, QA-12, QA-13, SC-2 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: `make check` in `packages/core` completes successfully.
- AC-2: Shared enums and models validate and serialize as documented.
- AC-3: Prompt loading accepts valid LangChain prompt JSON and rejects invalid file, JSON, and type inputs with explicit failures.
- AC-4: Prompt helpers shape ChatOpenAI kwargs without forwarding `None` options.
- AC-5: Public synthetic image helpers write image files and produce `data:image/png;base64,...` URLs with the documented failure semantics.
- AC-6: Image helpers accept only documented suffixes, return documented media types, build the documented multimodal message payload, and fail explicitly on unsupported formats, missing files, write failures, or PNG-encoding failure.
- AC-7: `build_tool_call_ai_message(...)` returns an `AIMessage` with exactly one caller-shaped tool call and default empty-string content.
- AC-8: Shared exceptions preserve the documented base-type split and remain distinct catch targets.

### Testing Strategy

**Framework and Constraints:**

- Use `pytest` as configured by `packages/core/pytest.ini`.
- Run unit tests with `uv run pytest -n auto tests/unit` through `make test-unit`.
- Reuse existing direct unit-test style with no skip markers.
- Reuse static checks from `make lint`: Ruff format/check, pylint max-module-lines, vulture, and jscpd.

**Unit:**

- Validate enums, models, serialization, and validation failures in `packages/core/tests/unit/core/test_models.py` and `packages/core/tests/unit/core/test_word_pairs.py`.
- Validate exceptions in `packages/core/tests/unit/core/test_exceptions.py`.
- Validate prompt loading, kwarg shaping, and AI tool-call message construction in `packages/core/tests/unit/core/test_prompts.py` and `packages/core/tests/unit/core/test_prompt_loading.py`.
- Validate image helpers, synthetic image generation, and synthetic image data-URL generation in `packages/core/tests/unit/core/test_image_encoding.py`.

**Integration:**

- N/A for the current package scope; the package exposes pure helpers and shared schemas, and its behavior is covered at unit level.

**Contract:**

- Treat enum values, model field sets, prompt-loading return type, exception types, synthetic image helper results, AI-message tool-call shape, and image-helper return shapes as contract surfaces verified by unit tests.

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
| QA-7 | FR-7, NFR-8 | Unit | `test_load_prompt_valid_file`, `test_load_prompt_missing_file`, `test_load_prompt_malformed_json`, `test_load_prompt_not_dict`, `test_load_prompt_wrong_langchain_type`, `test_load_prompt_round_trip`, `test_load_prompt_returns_stripped_content` | PR CI / local | Covers prompt success and fail-fast paths |
| QA-8 | FR-8 | Unit | `test_build_llm_kwargs_includes_only_non_none_values`, `test_build_llm_kwargs_preserves_all_explicit_values` | PR CI / local | Covers shared ChatOpenAI kwarg shaping |
| QA-9 | FR-9 | Unit | `test_validate_image_format_accepts_supported`, `test_validate_image_format_normalizes_suffix_case`, `test_validate_image_format_rejects_unsupported`, `test_validate_image_format_rejects_no_extension`, `test_supported_extensions_contains_expected_formats` | PR CI / local | Covers supported suffix policy |
| QA-10 | FR-10 | Unit | `test_encode_path_to_base64_returns_valid_base64`, `test_encode_path_to_base64_round_trips_file_content`, `test_encode_path_to_base64_jpeg_media_type`, `test_encode_path_to_base64_maps_other_media_types`, `test_encode_image_path_matches_encode_path_to_base64` | PR CI / local | Covers file-path encoding contract |
| QA-11 | FR-11, NFR-8 | Unit | `test_generate_test_image_writes_image_file` | PR CI / local | Covers shared synthetic image generation contract |
| QA-12 | FR-12, NFR-8 | Unit | `test_generate_test_image_data_url_returns_png_data_url`, `test_generate_test_image_data_url_decodes_to_non_empty_png_bytes` | PR CI / local | Covers shared synthetic image data-URL contract |
| QA-13 | FR-13, NFR-8 | Unit | `test_encode_cv2_to_base64_returns_png`, `test_encode_cv2_to_base64_preserves_pixel_data` | PR CI / local | Failure branch exists in implementation; success path is automated |
| QA-14 | FR-14 | Unit | `test_build_image_human_message_uses_data_url_payload` | PR CI / local | Covers shared multimodal image message shape |
| QA-15 | FR-15 | Unit | `test_build_tool_call_ai_message_defaults_content_to_empty_string`, `test_build_tool_call_ai_message_emits_single_tool_call` | PR CI / local | Covers generic AI tool-call message contract |
| QA-16 | FR-16 | Unit | `test_api_error_can_be_raised_and_caught`, `test_unsupported_image_format_error_can_be_raised_and_caught`, `test_target_language_not_found_in_input_error_can_be_raised_and_caught`, `test_unsupported_language_error_can_be_raised_and_caught`, `test_runtime_and_initialization_language_errors_have_expected_base_types`, `test_all_exceptions_are_subclasses_of_exception`, `test_exceptions_are_distinct_types` | PR CI / local | Covers exception hierarchy, role split, and independence |
| QA-17 | FR-17 | Unit | `test_load_prompt_round_trip` plus prompt serialization path in `prompt_author.py` contract | PR CI / local | Confirms `dumpd`/`load` compatibility |
| QA-18 | NFR-5 | Static | `uv run pylint ... --max-module-lines=200` via `make lint` | PR CI / local | Enforces file-size rule |
| QA-19 | NFR-6 | Static | `npx jscpd --config .jscpd.json --exitCode 1 src tests` via `make lint` | PR CI / local | Enforces zero duplication threshold |
| QA-20 | NFR-7 | Static | `uv run ruff check --fix src tests` using banned APIs in `ruff.toml` | PR CI / local | Rejects skip helpers and banned fallback APIs |

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
| RISK-1 | Shared schema or helper-contract changes in core can break multiple consumer packages immediately | High | Treat model, image-helper, and message-helper changes as cross-package changes and validate consumers before release |
| RISK-2 | Core carries NumPy/OpenCV dependencies for consumers that do not use image helpers | Low | Accept current trade-off unless package decomposition becomes necessary |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should prompt-authoring helpers receive direct unit tests instead of relying on shared `dumpd`/`load` compatibility coverage? | Open | Future package maintenance review | Current behavior is indirectly covered, but direct tests may improve confidence |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Kept as reviewed assumption documenting current repo topology | A-1 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open for future package hardening work | Revisit if prompt-authoring logic becomes more complex |

### Deferred Work

- D-1: Add direct tests for `serialize_prompt_to_json` and `save_prompt` if prompt-authoring behavior expands beyond the current thin wrapper.
