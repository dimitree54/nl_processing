---
Task ID: T2
Title: POS-specific NL->RU models + prompt generator scripts + prompt assets + tests
Sprint: 2026-03-13_extract-word-details
Module: extract_word_details
Depends on: T1
Parallelizable: no (T3 depends on this; T4 can run in parallel)
---

## Goal / value

After this task, all 13 Dutch POS types have explicit NL->RU Pydantic detailed models registered in the schema registry, and each POS has a prompt generator script plus a generated prompt JSON asset with few-shot examples. Schema consistency tests verify that prompts and models stay aligned. `make check` passes.

## Context (contract mapping)

- Module spec: `packages/extract_word_details/docs/module-spec.md` — FR-5 (explicit model per POS), FR-6 (Dutch lexical + Russian explanatory), FR-8 (shared learning fields), FR-10 (prompt assets per POS with few-shot examples), CR-1 (adding a POS requires model + prompt + tests together)
- Pattern reference: `packages/translate_word/src/nl_processing/translate_word/prompts/generate_nl_ru_prompt.py`

## Preconditions

- T1 complete: package scaffold exists, `_base_models.py`, `_schema_registry.py`, `_serializer.py` are implemented

## Non-goals

- Implementing the `WordDetailsExtractor` service (T3)
- Database or cache changes (T4, T5)
- Supporting language pairs beyond NL->RU

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- `packages/extract_word_details/` — source code and tests

**FORBIDDEN — this task must NEVER touch:**

- `packages/core/`, `packages/database/`, `packages/database_cache/`, or any other package
- Root configs

**Test scope:**

- Tests go in: `packages/extract_word_details/tests/unit/`
- Test command: `make check` in `packages/extract_word_details/`

## Touched surface (expected files / modules)

**New files to create:**

POS-specific model files (one per POS or grouped by similarity to respect 200-line limit):

- `src/nl_processing/extract_word_details/models/` directory with `__init__.py`
- `src/nl_processing/extract_word_details/models/_noun.py` — `NlRuNounDetails`
- `src/nl_processing/extract_word_details/models/_verb.py` — `NlRuVerbDetails`
- `src/nl_processing/extract_word_details/models/_adjective.py` — `NlRuAdjectiveDetails`
- `src/nl_processing/extract_word_details/models/_adverb.py` — `NlRuAdverbDetails`
- `src/nl_processing/extract_word_details/models/_preposition.py` — `NlRuPrepositionDetails`
- `src/nl_processing/extract_word_details/models/_conjunction.py` — `NlRuConjunctionDetails`
- `src/nl_processing/extract_word_details/models/_pronoun.py` — `NlRuPronounDetails`
- `src/nl_processing/extract_word_details/models/_article.py` — `NlRuArticleDetails`
- `src/nl_processing/extract_word_details/models/_numeral.py` — `NlRuNumeralDetails`
- `src/nl_processing/extract_word_details/models/_interjection.py` — `NlRuInterjectionDetails`
- `src/nl_processing/extract_word_details/models/_proper_noun.py` — `NlRuProperNounPersonDetails`, `NlRuProperNounCountryDetails`
- `src/nl_processing/extract_word_details/models/_phrase.py` — `NlRuPhraseDetails`
- `src/nl_processing/extract_word_details/models/_registry_init.py` — registers all models into the global schema registry

Prompt generator scripts and assets:

- `src/nl_processing/extract_word_details/prompts/` directory with `__init__.py`
- One `generate_nl_ru_{pos}_prompt.py` per POS (or grouped if small enough — respect 200-line limit)
- One generated `nl_ru_{pos}.json` per POS

Tests:

- `tests/unit/extract_word_details/test_pos_models.py` — construction and serialization tests for all 13 POS models
- `tests/unit/extract_word_details/test_registry_init.py` — verify all 13 POS are registered, schema keys correct, round-trip works
- `tests/unit/extract_word_details/test_prompt_consistency.py` — verify each prompt JSON loads correctly, matches its POS model schema

## Dependencies and sequencing notes

- Depends on T1 for base models, schema registry, and serializer
- T3 depends on this for POS models and prompt assets
- T4 can start in parallel (only needs schema registry from T1)

## Third-party / library research (mandatory for any external dependency)

- **Library**: `pydantic` v2.x — used for all POS-specific detailed models
  - **Relevant docs**: https://docs.pydantic.dev/latest/concepts/models/
  - **Usage**: Each POS model is a `BaseModel` subclass with typed fields. `model_dump()` for serialization, `model_validate()` for parsing.

- **Library**: `langchain-core` v0.3 — used for prompt template construction
  - **Relevant docs**: https://python.langchain.com/docs/concepts/prompt_templates/
  - **API reference**: `ChatPromptTemplate.from_messages()`, `SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`, `MessagesPlaceholder`
  - **Usage**: Follow the exact pattern from `translate_word/prompts/generate_nl_ru_prompt.py` — build a `ChatPromptTemplate` with system instruction, few-shot examples using tool calls, and a `MessagesPlaceholder`.
  - **Serialization**: Use `nl_processing.core.scripts.prompt_author.save_prompt()` to serialize to JSON.

- **Key difference from `translate_word`**: Each POS gets its own prompt and tool schema (a batch wrapper around the POS-specific model), whereas `translate_word` has one universal prompt. The system instruction must instruct the LLM to return detailed linguistic data for that specific POS in Dutch with Russian explanations.

## Implementation steps (developer-facing)

1. **Create `models/` directory** with `__init__.py` that re-exports all POS model classes.

2. **Implement each POS model** as a Pydantic `BaseModel` that includes:
   - POS-specific linguistic fields (Dutch lexical material)
   - Russian explanatory content
   - `SharedLearningFields` (from `_base_models.py`)

   **Field design per POS** (OQ-1 resolution — dev defines reasonable fields):

   - **Noun** (`NlRuNounDetails`): `article` (de/het), `plural`, `diminutive`, `gender_explanation` (RU), `shared` (SharedLearningFields)
   - **Verb** (`NlRuVerbDetails`): `present_tense` (ik/jij/hij/wij/zij forms), `past_simple`, `past_participle`, `auxiliary` (hebben/zijn), `separable_prefix` (if applicable), `conjugation_explanation` (RU), `shared` (SharedLearningFields)
   - **Adjective** (`NlRuAdjectiveDetails`): `comparative`, `superlative`, `inflected_form` (with -e), `usage_explanation` (RU), `shared` (SharedLearningFields)
   - **Adverb** (`NlRuAdverbDetails`): `usage_context` (RU), `position_in_sentence` (RU), `shared` (SharedLearningFields)
   - **Preposition** (`NlRuPrepositionDetails`): `case_governance` (RU — what follows this prep), `spatial_or_temporal` (RU), `shared` (SharedLearningFields)
   - **Conjunction** (`NlRuConjunctionDetails`): `conjunction_type` (coordinating/subordinating, RU), `word_order_effect` (RU), `shared` (SharedLearningFields)
   - **Pronoun** (`NlRuPronounDetails`): `pronoun_type` (personal/possessive/demonstrative/etc., RU), `declension_forms` (list of forms), `shared` (SharedLearningFields)
   - **Article** (`NlRuArticleDetails`): `article_type` (definite/indefinite, RU), `gender_rules` (RU), `shared` (SharedLearningFields)
   - **Numeral** (`NlRuNumeralDetails`): `numeral_type` (cardinal/ordinal, RU), `ordinal_form`, `shared` (SharedLearningFields)
   - **Interjection** (`NlRuInterjectionDetails`): `emotion_or_context` (RU), `formality_level` (RU), `shared` (SharedLearningFields)
   - **Proper noun (person)** (`NlRuProperNounPersonDetails`): `origin_explanation` (RU), `cultural_context` (RU), `shared` (SharedLearningFields)
   - **Proper noun (country)** (`NlRuProperNounCountryDetails`): `dutch_name`, `russian_name`, `nationality_adjective` (NL), `nationality_noun` (NL), `cultural_context` (RU), `shared` (SharedLearningFields)
   - **Phrase** (`NlRuPhraseDetails`): `literal_translation` (RU), `figurative_meaning` (RU), `usage_context` (RU), `shared` (SharedLearningFields)

3. **Create `_registry_init.py`** that:
   - Imports all 13 POS model classes
   - Creates the global `SCHEMA_REGISTRY` instance
   - Registers each POS model with its `schema_key` (pattern: `nl_ru_{pos_value}`) and `schema_version` (all start at `1`)
   - Exports `SCHEMA_REGISTRY` for use by other modules

4. **Create prompt generator scripts** following the `translate_word` pattern:
   - Each script builds a `ChatPromptTemplate` with:
     - System instruction in Russian explaining the task for that specific POS
     - 2-3 few-shot examples using tool calls (AIMessage with tool_call + ToolMessage)
     - `MessagesPlaceholder(variable_name="text")` for input
   - Each POS needs a batch wrapper model (e.g., `_NounDetailsBatch(BaseModel)` with `details: list[NlRuNounDetails]`) for `bind_tools`
   - Run each script with `uv run python src/nl_processing/extract_word_details/prompts/generate_nl_ru_{pos}_prompt.py` to produce the JSON
   - Scripts are the source of truth; JSON files are generated artifacts

   **Grouping**: If 13 individual generator scripts would be too granular, group related POS into shared scripts (e.g., one script for proper_noun_person + proper_noun_country). Respect the 200-line file limit.

5. **Write unit tests:**

   - `test_pos_models.py`: For each of the 13 POS models, test:
     - Valid construction with all fields
     - `model_dump()` produces expected dict structure
     - `model_validate()` round-trips correctly
     - Missing required fields raise validation error

   - `test_registry_init.py`:
     - Verify all 13 POS are registered in `SCHEMA_REGISTRY`
     - Verify schema_key naming convention is correct for each POS
     - Verify all versions are 1 (initial)
     - Verify round-trip: serialize a model instance → `model_dump()` → `parse_payload()` → get back equivalent instance

   - `test_prompt_consistency.py`:
     - For each POS, verify the corresponding `nl_ru_{pos}.json` file exists and can be loaded with `langchain_core.load.load()`
     - Verify the loaded prompt is a `ChatPromptTemplate`
     - Verify it contains a `MessagesPlaceholder` for "text"

6. **Verify**: Run `make check` in `packages/extract_word_details/`. All tests pass, lint passes, no file exceeds 200 lines.

## Production safety constraints (mandatory)

- **Database operations**: None in this task. All models and prompts are static assets.
- Prompt generator scripts do not call external APIs — they only build and serialize prompt templates.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Reuse `SharedLearningFields` from `_base_models.py`. Reuse `SchemaRegistry` from `_schema_registry.py`. Reuse `save_prompt()` from `nl_processing.core.scripts.prompt_author`.
- **Correct libraries only**: `pydantic>=2.0,<3`, `langchain-core>=0.3,<1` — matching root and package manifests.
- **Correct file locations**: Models under `models/`, prompts under `prompts/`, tests under `tests/unit/`.
- **No regressions**: New package — no existing code affected.

## Error handling + correctness rules (mandatory)

- POS models must not use `dict[str, Any]` for any field — all fields must be concretely typed.
- Model validation errors must propagate as Pydantic `ValidationError`, not be caught and hidden.
- Prompt generator scripts must fail if `save_prompt()` fails — no silent fallback.

## Zero legacy tolerance rule (mandatory)

- No generic/fallback models — every POS has its own explicit model.
- No placeholder "TODO" models — all 13 POS must be fully defined.

## Acceptance criteria (testable)

1. All 13 POS types (NOUN, VERB, ADJECTIVE, ADVERB, PREPOSITION, CONJUNCTION, PRONOUN, ARTICLE, NUMERAL, INTERJECTION, PROPER_NOUN_PERSON, PROPER_NOUN_COUNTRY, PHRASE) have explicit NL->RU Pydantic models.
2. All 13 models include POS-specific fields plus `SharedLearningFields`.
3. All 13 models are registered in `SCHEMA_REGISTRY` with `schema_key` pattern `nl_ru_{pos_value}` and `schema_version=1`.
4. Each POS has a prompt generator script and a generated `nl_ru_{pos_value}.json` prompt asset.
5. Schema consistency tests verify prompt/model compatibility for all 13 POS.
6. Round-trip serialization tests pass for all 13 POS models.
7. `make check` passes in `packages/extract_word_details/`.
8. No file exceeds 200 lines.

## Verification / quality gates

- [x] Unit tests added for all 13 POS models (construction, serialization, round-trip)
- [x] Unit tests verify registry completeness (all 13 registered)
- [x] Unit tests verify prompt consistency (all 13 prompts loadable and well-formed)
- [x] Linters/formatters pass
- [x] No new warnings introduced
- [x] No file exceeds 200 lines

## Edge cases

- POS models with optional fields (e.g., verb `separable_prefix` is not applicable for all verbs): use `str | None` with default `None`
- Proper noun subtypes: `PROPER_NOUN_PERSON` and `PROPER_NOUN_COUNTRY` are separate POS values and need separate models and prompts
- `PHRASE` POS: not a traditional part of speech, but it's in the `PartOfSpeech` enum and needs its own model

## Notes / risks

- **OQ-1 resolution**: The exact per-POS field matrix is open in the spec. The dev must define reasonable fields based on linguistic needs. The field sets described in step 2 are a concrete starting point — the dev may adjust based on their linguistic judgment, but every model must include both Dutch lexical fields and Russian explanatory fields plus `SharedLearningFields`.
- **File count**: 13 model files + 13 prompt scripts + 13 JSON assets = 39 files. Some grouping may be needed to keep things manageable. The dev should use judgment about when to group similar POS (e.g., both proper noun subtypes in one file) vs. keep separate.
- **200-line limit**: Prompt generator scripts with multiple few-shot examples can get long. Keep examples concise and split into helper functions if needed.
