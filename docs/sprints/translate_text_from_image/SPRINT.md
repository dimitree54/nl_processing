---
Sprint ID: `translate_text_from_image`
Sprint Goal: Implement a production-ready `translate_text_from_image` module that translates Dutch text from images to Russian in a single LLM call.
Sprint Type: module
Module: `translate_text_from_image`
Status: planning
---

## Goal

Deliver the `translate_text_from_image` package: a standalone multimodal service that accepts an image (file path or cv2 array), performs one LLM call to extract and translate Dutch text to Russian, and returns clean markdown output. The module must pass the full curated quality corpus (simple, multiline, mixed-language, vocabulary, rotated, product-box) and integrate cleanly with the monorepo build system.

## Module Scope

### What this sprint implements
- Module: `translate_text_from_image`
- Module spec: `packages/translate_text_from_image/docs/module-spec.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `packages/translate_text_from_image/` — new package (all source, tests, config)
- `packages/core/src/nl_processing/core/prompts.py` — extend `build_translation_chain()` with optional kwargs
- `packages/core/src/nl_processing/core/image_encoding.py` — new shared image helpers (promoted from `extract_text_from_image`)
- `packages/core/src/nl_processing/core/__init__.py` — only if needed for image_encoding exports
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/image_encoding.py` — replace with re-exports from core
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/service.py` — update imports from core
- `packages/extract_text_from_image/src/nl_processing/extract_text_from_image/prompts/generate_nl_prompt.py` — update imports from core
- `Makefile` (root) — add `translate_text_from_image` to `PACKAGES`
- `ruff.toml` (root) — add new package `src` path
- `vulture_whitelist.py` (root) — add new module's public API

**FORBIDDEN — this sprint must NEVER touch:**
- `packages/translate_text/` — no changes
- `packages/extract_words_from_text/` — no changes
- `packages/translate_word/` — no changes
- `packages/database/` — no changes
- `packages/database_cache/` — no changes
- `packages/sampling/` — no changes
- Any bot-layer code

### Test Scope
- **Test directory**: `packages/translate_text_from_image/tests/`
- **Test command**: `make -C packages/translate_text_from_image check`
- **Also verify**: `make -C packages/extract_text_from_image check` (after image helper promotion)
- **NEVER run**: full `make check` until final integration task

## Interface Contract

### Public interface this sprint implements

```python
class ImageTextTranslator:
    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        reasoning_effort: str | None = None,
        service_tier: str | None = None,
        temperature: float | None = 0,
    ) -> None: ...

    async def translate_from_path(self, path: str) -> str: ...
    async def translate_from_cv2(self, image: numpy.ndarray) -> str: ...
```

## Scope

### In
- Promote image helpers (`validate_image_format`, `encode_path_to_base64`, `encode_cv2_to_base64`, `SUPPORTED_EXTENSIONS`) to `core`
- Extend `build_translation_chain()` with optional `reasoning_effort`, `service_tier`, `temperature` kwargs
- New package scaffolding (`pyproject.toml`, `Makefile`, `pytest.ini`, `ruff.toml`, `__init__.py` files)
- `ImageTextTranslator` service with `translate_from_path()` and `translate_from_cv2()`
- Multimodal prompt generator script + `nl_ru.json` prompt asset + few-shot example images
- Unit, integration, and e2e tests
- Root build system integration (`Makefile`, `ruff.toml`, `vulture_whitelist.py`)

### Out
- Language pairs other than `nl -> ru`
- Runtime fallback to `extract_text_from_image` + `translate_text` chain
- OCR fallback
- Returning intermediate extracted Dutch text
- Batch orchestration, caching, streaming
- `translate_base64` API (OQ-3 — deferred)

## Inputs (contracts)

- Module spec: `packages/translate_text_from_image/docs/module-spec.md`
- Core package: `packages/core/src/nl_processing/core/`
- Reference pattern (extraction): `packages/extract_text_from_image/`
- Reference pattern (translation): `packages/translate_text/`
- Build system: root `Makefile`, `ruff.toml`, `.jscpd.json`, `vulture_whitelist.py`

## Change digest

- **Requirement deltas**: New module implementing FR-1 through FR-12 from module-spec.
- **Architecture deltas**: DEC-3 requires promoting image helpers to core; DEC-2 requires extending `build_translation_chain()`.

## Task list (dependency-aware)

- **T1:** `TASK_1_promote_image_helpers_to_core.md` (depends: --) — Promote image encoding helpers from `extract_text_from_image` to `core`
- **T2:** `TASK_2_extend_build_translation_chain.md` (depends: --) (parallel: yes, with T1) — Extend `build_translation_chain()` with optional LLM kwargs
- **T3:** `TASK_3_package_scaffolding.md` (depends: T1, T2) — Create `translate_text_from_image` package scaffolding + root build integration
- **T4:** `TASK_4_service_and_unit_tests.md` (depends: T3) — Implement `ImageTextTranslator` service + unit tests
- **T5:** `TASK_5_prompt_generation_and_assets.md` (depends: T3) (parallel: yes, with T4) — Create prompt generator script, seed examples, generate `nl_ru.json`
- **T6:** `TASK_6_integration_tests.md` (depends: T4, T5) — Integration tests (live API): simple, multiline, mixed-language, English-only, latency
- **T7:** `TASK_7_e2e_tests.md` (depends: T6) — E2e tests: real photo vocabulary, rotated page, product box quality
- **T8:** `TASK_8_final_integration.md` (depends: T7) — Final integration: vulture whitelist, full `make check` validation

## Dependency graph (DAG)

```
T1 ──┐
     ├──→ T3 ──→ T4 ──┐
T2 ──┘         ↘       ├──→ T6 ──→ T7 ──→ T8
                T5 ────┘
```

- T1 → T3
- T2 → T3
- T3 → T4
- T3 → T5
- T4 → T6
- T5 → T6
- T6 → T7
- T7 → T8

## Execution plan

### Critical path
T1 → T3 → T4 → T6 → T7 → T8

### Parallel tracks (lanes)
- **Lane A (foundation)**: T1 || T2, then T3
- **Lane B (service)**: T4 (after T3)
- **Lane C (prompts)**: T5 (after T3, parallel with T4)
- **Lane D (testing)**: T6, T7 (sequential, after T4+T5)
- **Lane E (integration)**: T8 (final)

## Production safety

- **Production database**: N/A — this module has no database operations.
- **Shared resource isolation**: Module only uses OpenAI API (same key as production, but only for test calls — no state mutations). No file paths, ports, or sockets conflict with production.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks T1–T8 completed and verified
- Package tests pass: `make -C packages/translate_text_from_image check`
- Existing extraction tests pass: `make -C packages/extract_text_from_image check`
- Full repo check passes: `make check` (root)
- Module isolation: only ALLOWED files were touched
- Public interface matches module spec exactly
- Zero legacy tolerance: `extract_text_from_image` updated to import from core (no duplicated image helpers)
- No errors are silenced
- jscpd passes (no duplicated 10+ line blocks)
- All files under 200 lines

## Risks + mitigations

- **Risk**: Promoting image helpers to core may break `extract_text_from_image` tests.
  - **Mitigation**: T1 explicitly includes running `make -C packages/extract_text_from_image check` as acceptance criteria.
- **Risk**: Single multimodal prompt may underperform the two-call chain on complex images (RISK-2 from spec).
  - **Mitigation**: E2e tests in T7 use the same curated corpus; quality failures are caught before merge.
- **Risk**: jscpd detects duplication between new prompt generator and existing ones.
  - **Mitigation**: Each task explicitly calls out jscpd constraints; prompt content is unique (Russian translations of image content vs. text-only).
- **Risk**: `build_translation_chain()` extension could break existing `translate_text` callers.
  - **Mitigation**: Extension is purely additive (optional kwargs with defaults matching current behavior). T2 includes running `translate_text` tests.
- **Risk**: Shared error contract for "source language not found" is unresolved (OQ-1).
  - **Mitigation**: Sprint reuses `TargetLanguageNotFoundError` from core (semantically close enough; rename is deferred).

## Migration plan

N/A — no data model changes.

## Rollback / recovery notes

- Revert the PR. The only cross-package changes are: image helpers in core (additive), `build_translation_chain` kwargs (backward-compatible), and build system entries (removable).

## Task validation status

- T1: planned
- T2: planned
- T3: planned
- T4: planned
- T5: planned
- T6: planned
- T7: planned
- T8: planned

## Sources used

- Module spec: `packages/translate_text_from_image/docs/module-spec.md`
- Core: `packages/core/src/nl_processing/core/` (exceptions.py, prompts.py, models.py, scripts/prompt_author.py)
- Extract pattern: `packages/extract_text_from_image/` (service.py, image_encoding.py, prompts/, tests/)
- Translate pattern: `packages/translate_text/` (service.py, prompts/, tests/)
- Build: root Makefile, ruff.toml, .jscpd.json, vulture_whitelist.py

## Contract summary

### What (requirements)
- FR-1 through FR-12: multimodal single-call image translation service (NL→RU)
- NFR-1: <10s latency on simple fixtures
- NFR-2: 100% pass on curated quality corpus
- NFR-3: Generated prompt JSON from script
- NFR-4: Shared image helpers in core

### How (architecture)
- DEC-1: Standalone one-call service, not orchestration
- DEC-2: Reuse `build_translation_chain()` from core
- DEC-3: Promote image helpers to core
- DEC-4/5: Seed few-shot examples locally, use reviewed golden outputs
- DEC-6: Return only translated text
- DEC-7: No runtime fallbacks

## Impact inventory

- **Module**: `translate_text_from_image` — `packages/translate_text_from_image/`
- **Interfaces**: `ImageTextTranslator.translate_from_path()`, `ImageTextTranslator.translate_from_cv2()`
- **Data model**: `_TranslatedImageText` (internal Pydantic tool schema)
- **External services**: OpenAI API (multimodal vision + tool calling)
- **Shared code changes**: `core/image_encoding.py` (new), `core/prompts.py` (extended)
- **Test directory**: `packages/translate_text_from_image/tests/`
