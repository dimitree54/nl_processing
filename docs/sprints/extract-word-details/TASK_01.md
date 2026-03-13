---
Task ID: T1
Title: Scaffold `extract_word_details` package + core types + schema registry
Sprint: 2026-03-13_extract-word-details
Module: extract_word_details
Depends on: —
Parallelizable: no (foundation task)
---

## Goal / value

After this task, the `extract_word_details` package exists as a valid, buildable package with `pyproject.toml`, `Makefile`, `pytest.ini`, `ruff.toml`, and directory structure. The core types (base detailed-model fields, shared learning fields), the versioned schema registry, and the serializer contract are implemented and tested. `make check` passes with unit tests green.

## Context (contract mapping)

- Module spec: `packages/extract_word_details/docs/module-spec.md` — FR-9 (versioned schema registry + serializer contract), FR-5 (explicit Pydantic models per POS), FR-8 (shared learning fields)
- Database spec: `packages/database/docs/module-spec.md` — FR-12 (schema_key, schema_version, validated JSON payload), CR-4 (round-trip through extractor-owned registry)
- Database cache spec: `packages/database_cache/docs/module-spec.md` — FR-14 (round-trip through shared schema registry)
- Existing pattern reference: `packages/translate_word/` (pyproject.toml, Makefile, ruff.toml, pytest.ini structure)

## Preconditions

- Root repo exists with the standard monorepo layout
- `packages/extract_word_details/docs/module-spec.md` exists (confirmed)
- No source code, tests, or configs exist in `packages/extract_word_details/` yet (confirmed)

## Non-goals

- Implementing POS-specific models (T2)
- Implementing the extractor service (T3)
- Implementing prompt assets (T2)
- Updating root Makefile/pyproject.toml (T6)

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `packages/extract_word_details/` — all files (creating from scratch)

**FORBIDDEN — this task must NEVER touch:**

- `packages/core/` — shared types are already sufficient
- `packages/database/` — separate task (T4)
- `packages/database_cache/` — separate task (T5)
- Root configs — separate task (T6)
- Any other package

**Test scope:**

- Tests go in: `packages/extract_word_details/tests/unit/`
- Test command: `make check` in `packages/extract_word_details/`
- NEVER run the full test suite or tests from other modules

## Touched surface (expected files / modules)

**New files to create:**

- `packages/extract_word_details/pyproject.toml`
- `packages/extract_word_details/Makefile`
- `packages/extract_word_details/pytest.ini`
- `packages/extract_word_details/ruff.toml`
- `packages/extract_word_details/src/nl_processing/__init__.py` (empty, namespace)
- `packages/extract_word_details/src/nl_processing/extract_word_details/__init__.py` (empty)
- `packages/extract_word_details/src/nl_processing/extract_word_details/_base_models.py` — shared base fields, learning fields
- `packages/extract_word_details/src/nl_processing/extract_word_details/_schema_registry.py` — versioned schema registry
- `packages/extract_word_details/src/nl_processing/extract_word_details/_serializer.py` — serialize/parse contract
- `packages/extract_word_details/tests/__init__.py`
- `packages/extract_word_details/tests/unit/__init__.py`
- `packages/extract_word_details/tests/unit/extract_word_details/__init__.py`
- `packages/extract_word_details/tests/unit/extract_word_details/test_schema_registry.py`
- `packages/extract_word_details/tests/unit/extract_word_details/test_serializer.py`
- `packages/extract_word_details/tests/unit/extract_word_details/test_base_models.py`

## Dependencies and sequencing notes

- This is the foundation task. All other tasks depend on it.
- The schema registry contract is consumed by T4 (`database.DetailedWordStore`) and T5 (`database_cache.DetailedWordCacheService`), so it must be stable before those tasks begin.
- T2 (POS-specific models) extends the base models created here.

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` v2.x (already in repo: `>=2.0,<3`)
  - **Official docs**: https://docs.pydantic.dev/latest/
  - **Relevant**: `BaseModel`, `model_dump()`, `model_validate()`, discriminated unions
  - **Usage**: Base detailed models use `BaseModel`. Serializer uses `model_dump()` and `model_validate()`.
  - **Known gotchas**: v2 uses `model_dump()` not `.dict()`. Field aliases need `populate_by_name=True` if used.

- **Library**: `langchain-core` v0.3 (already in repo: `>=0.3,<1`)
  - **Official docs**: https://python.langchain.com/docs/
  - **Relevant for T1**: Not directly used yet — just declared as dependency for later tasks.

- **Library**: `langchain-openai` v0.3 (already in repo: `>=0.3,<1`)
  - **Official docs**: https://python.langchain.com/docs/integrations/chat/openai/
  - **Relevant for T1**: Not directly used yet — declared as dependency for later tasks.

## Implementation steps (developer-facing)

1. **Create `pyproject.toml`** following the `translate_word` pattern:
   - Name: `nl-processing-extract-word-details`
   - Dependencies: `nl-processing-core`, `langchain-core>=0.3,<1`, `langchain-openai>=0.3,<1`, `pydantic>=2.0,<3`
   - Dev dependencies: same as `translate_word` (pytest, pytest-asyncio, pytest-xdist, ruff, pylint, vulture)
   - `[tool.uv.sources]`: `nl-processing-core = { path = "../core" }`
   - `[tool.setuptools.packages.find]`: `where = ["src"]`, `include = ["nl_processing.extract_word_details*"]`, `namespaces = true`
   - `[tool.setuptools.package-data]`: `"nl_processing.extract_word_details.prompts" = ["*.json"]`

2. **Create `Makefile`** following the pattern:
   ```makefile
   ROOT_DIR := $(abspath ../..)
   TOOLS_VENV ?= $(shell if [ -x "$(CURDIR)/.venv/bin/pytest" ] && [ -x "$(CURDIR)/.venv/bin/ruff" ] && [ -x "$(CURDIR)/.venv/bin/pylint" ] && [ -x "$(CURDIR)/.venv/bin/vulture" ]; then printf '%s' "$(CURDIR)/.venv"; else printf '%s' "$(ROOT_DIR)/.venv"; fi)
   .PHONY: check
   check:
   	$(MAKE) -C "$(ROOT_DIR)" package-check PKG=extract_word_details PACKAGE_PYTHONPATH=src:../core/src TOOLS_VENV="$(TOOLS_VENV)"
   ```

3. **Create `pytest.ini`** — copy from `translate_word/pytest.ini` verbatim.

4. **Create `ruff.toml`** — copy from `translate_word/ruff.toml` verbatim (`extend = "../../ruff.toml"`, `src = ["src", "tests"]`).

5. **Create directory structure:**
   - `src/nl_processing/__init__.py` (empty)
   - `src/nl_processing/extract_word_details/__init__.py` (empty)
   - `tests/__init__.py` (empty)
   - `tests/unit/__init__.py` (empty)
   - `tests/unit/extract_word_details/__init__.py` (empty)

6. **Implement `_base_models.py`** — shared base fields used by all POS-specific models:
   - `CommonPhrases` model: list of phrase + translation pairs relevant to the word
   - `ExampleSentence` model: Dutch sentence + Russian explanation
   - `WordPartExplanation` model: morpheme/root explanation
   - `InterestingFact` model: cultural/linguistic fact with optional NL-RU parallel
   - `SharedLearningFields` model: common_phrases, example_sentences, word_parts, interesting_facts (FR-8)
   - All explanatory text fields are in Russian (target language) per FR-6 and DEC-4

7. **Implement `_schema_registry.py`** — the versioned schema registry (FR-9):
   - `SchemaRegistryEntry` dataclass: `schema_key: str`, `schema_version: int`, `model_class: type[BaseModel]`
   - `SchemaRegistry` class with:
     - `register(schema_key, schema_version, model_class)` — register a POS model
     - `get_entry(schema_key, schema_version) -> SchemaRegistryEntry` — look up by key+version, raise if not found
     - `get_current_version(schema_key) -> int` — get the latest registered version for a key
     - `is_compatible(schema_key, schema_version) -> bool` — check if a version is registered
   - The registry is populated at module import time (by POS model modules in T2). For T1, provide the class and infrastructure but register only a test/example entry for testing.
   - The `schema_key` pattern is `{src}_{tgt}_{pos}` (e.g., `nl_ru_noun`)

8. **Implement `_serializer.py`** — the shared serialization contract (FR-9, CR-3):
   - `serialize_payload(record: BaseModel) -> dict[str, ...]` — calls `model_dump()` and returns the payload dict
   - `parse_payload(schema_key: str, schema_version: int, payload: dict, registry: SchemaRegistry) -> BaseModel` — looks up the registry entry, validates with `model_validate()`, raises `PayloadValidationError` on failure, raises `SchemaVersionError` on unknown version
   - Import the exception types from `nl_processing.database.detailed_exceptions` (they already exist in database)

   **IMPORTANT**: The serializer must import from `nl_processing.database.detailed_exceptions`. Since `extract_word_details` does not depend on `database`, define local exception types in `_exceptions.py` that mirror the database ones. The database module will catch these by name/type. Alternatively, add `nl-processing-database` as a dependency — but that would create a circular dependency since `database` depends on `extract_word_details` for the extractor port. Therefore: define the exceptions locally in `extract_word_details` and keep the packages decoupled. The `_serializer.py` raises `SchemaVersionError` and `PayloadValidationError` defined locally.

   Create `_exceptions.py`:
   - `SchemaVersionError(Exception)` — raised when schema version is unknown
   - `PayloadValidationError(Exception)` — raised when payload fails validation

9. **Write unit tests:**
   - `test_base_models.py`: test construction, serialization, validation of all shared learning-field models
   - `test_schema_registry.py`: test register, get_entry, get_current_version, is_compatible, unknown-key error, unknown-version error
   - `test_serializer.py`: test serialize_payload round-trip, parse_payload with valid data, parse_payload with invalid data (expect error), parse_payload with unknown schema_version (expect error)

10. **Verify**: Run `make check` in `packages/extract_word_details/`. All unit tests pass, lint passes, no files exceed 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: None in this task. Pure in-memory types and registry.
- This task creates a brand-new package with no external service dependencies.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse `Word`, `Language`, `PartOfSpeech` from `nl_processing.core.models`. Reuse `DetailedWordRecord` from `nl_processing.database.detailed_models` as the public output type (but do NOT add database as a dependency — reference it conceptually; the actual `DetailedWordRecord` is constructed by the service in T3).
- **Correct libraries only**: All versions match root `pyproject.toml` and existing package patterns.
- **Correct file locations**: Follow monorepo package layout exactly as `translate_word`.
- **No regressions**: This is a new package — no existing code is affected.

## Error handling + correctness rules (mandatory)

- Schema registry lookups for unknown keys or versions must raise explicit errors, never return None or a default.
- Serializer must raise `PayloadValidationError` for invalid data, never coerce partial models.
- Serializer must raise `SchemaVersionError` for unknown versions, never fall back to latest.

## Zero legacy tolerance rule (mandatory)

- This is a greenfield package — no legacy to clean up.
- All code must be production-quality from the start.

## Acceptance criteria (testable)

1. `packages/extract_word_details/pyproject.toml` exists and follows the `translate_word` pattern with correct name, dependencies, and package config.
2. `packages/extract_word_details/Makefile`, `pytest.ini`, `ruff.toml` exist and follow established patterns.
3. `_base_models.py` defines `CommonPhrases`, `ExampleSentence`, `WordPartExplanation`, `InterestingFact`, `SharedLearningFields` as Pydantic models.
4. `_schema_registry.py` defines `SchemaRegistry` with `register()`, `get_entry()`, `get_current_version()`, `is_compatible()` methods.
5. `_serializer.py` defines `serialize_payload()` and `parse_payload()` with proper error handling.
6. `_exceptions.py` defines `SchemaVersionError` and `PayloadValidationError`.
7. Unit tests cover: base model construction/serialization, registry CRUD, registry error paths, serializer round-trip, serializer error paths.
8. `make check` passes in `packages/extract_word_details/` (lint + unit tests).
9. No file exceeds 200 lines.

## Verification / quality gates

- [x] Unit tests added (test_base_models, test_schema_registry, test_serializer)
- [x] Linters/formatters pass (`ruff format`, `ruff check`, `pylint` module-lines + bad-builtins)
- [x] No new warnings introduced
- [x] Negative-path tests exist (unknown schema key, unknown version, invalid payload)
- [x] No file exceeds 200 lines

## Edge cases

- Schema registry with no entries registered: `get_entry()` must raise, not return None
- `parse_payload()` with a payload that partially matches the model: must raise `PayloadValidationError`, not silently drop fields
- Empty `SharedLearningFields` (all empty lists): must be valid — a word might have no phrases yet

## Notes / risks

- The `_serializer.py` exceptions are defined locally in `extract_word_details`, not imported from `database`. This avoids a circular dependency. The `database` module will need to catch/translate these when calling the extractor. T4 must handle this.
- The schema_key naming convention (`{src}_{tgt}_{pos}`) must be consistent across all three modules. This is established here and consumed by T4/T5.
