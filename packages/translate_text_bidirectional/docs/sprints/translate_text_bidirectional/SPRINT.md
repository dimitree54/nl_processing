---
Sprint ID: `2026-03-12_translate-text-bidirectional`
Sprint Goal: `Implement the translate_text_bidirectional package: a bidirectional NL<->RU translator with model-decided tool choice, full test suite, and monorepo integration.`
Sprint Type: `module`
Module: `translate_text_bidirectional`
Status: `planning`
---

## Goal

Deliver a fully working `translate_text_bidirectional` Python package that translates text bidirectionally between Dutch and Russian. The module infers translation direction from input language using two direction-specific model tools with model-decided tool choice. All tests pass, `make check` is green, and the package is integrated into the monorepo.

## Module Scope

### What this sprint implements
- Module: `translate_text_bidirectional`
- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md`

### Boundary Rules (STRICTLY ENFORCED)

**ALLOWED — this sprint may ONLY touch:**
- `packages/translate_text_bidirectional/` — all files (new package)
- `packages/core/src/nl_processing/core/prompts.py` — extend with multi-tool chain builder (T1 only)
- `packages/core/src/nl_processing/core/__init__.py` — if needed for exports
- Root `pyproject.toml` — add package entries for monorepo integration (T7 only)
- Root `Makefile` — add to PACKAGES list (T7 only)
- Root `ruff.toml` — add src path (T7 only)
- Root `vulture_whitelist.py` — add entries if needed (T7 only)

**FORBIDDEN — this sprint must NEVER touch:**
- `packages/translate_text/` — sibling package (reference only)
- `packages/translate_text_from_image/` — sibling package
- Any other package's source code or tests
- `docs/module-spec.md` — the spec is read-only

### Test Scope
- **Test directory**: `packages/translate_text_bidirectional/tests/`
- **Test command**: `make check` (from package directory)
- **NEVER run**: full monorepo test suite during development

## Interface Contract

### Public interface this sprint implements
```python
class BidirectionalTextTranslator:
    def __init__(
        self,
        *,
        source_language: Language,
        target_language: Language,
        model: str = "gpt-4.1-mini",
        service_tier: str | None = "priority",
    ) -> None: ...

    async def translate(self, text: str) -> str: ...
```

## Scope

### In
- Core extension: `build_bidirectional_translation_chain` in `core/prompts.py`
- Package scaffolding: `pyproject.toml`, `Makefile`, `pytest.ini`, `ruff.toml`, src layout
- Prompt asset: `prompts/generate_nl_ru_bidirectional_prompt.py` + generated `nl_ru_bidirectional.json`
- Service: `BidirectionalTextTranslator` with multi-tool direction inference
- Unit tests: constructor, blank input, error wrapping, tool parsing
- Integration tests: live API both directions, markdown preservation, script checks, performance
- E2E tests: full translation both directions, product-box quality both directions
- Monorepo integration: root `pyproject.toml`, `Makefile`, `ruff.toml`

### Out
- Language pairs beyond `nl <-> ru`
- Mixed-input acceptance tests (FR-9 deferred per spec)
- Changes to `translate_text` or any other sibling package
- Caching, streaming, glossaries, persistence

## Inputs (contracts)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md`
- Reference implementation: `packages/translate_text/` (patterns to mirror)
- Core infrastructure: `packages/core/src/nl_processing/core/prompts.py`
- Root monorepo config: `pyproject.toml`, `Makefile`, `ruff.toml`

## Change digest

- **Requirement deltas**: New module from scratch — no prior implementation exists.
- **Architecture deltas**: `core/prompts.py` must grow a `build_bidirectional_translation_chain` function to support multiple tools with model-decided tool choice, without regressing the existing `build_translation_chain`.

## Task list (dependency-aware)

- **T1:** `TASK_T1.md` (depends: —) — Extend core with multi-tool chain builder
- **T2:** `TASK_T2.md` (depends: T1) — Package scaffolding
- **T3:** `TASK_T3.md` (depends: T2) — Bidirectional prompt asset
- **T4:** `TASK_T4.md` (depends: T3) — Service implementation with unit tests
- **T5:** `TASK_T5.md` (depends: T4) — Integration tests (live API, both directions)
- **T6:** `TASK_T6.md` (depends: T5) — E2E tests (full translation + quality, both directions)
- **T7:** `TASK_T7.md` (depends: T6) — Monorepo integration and final verification

## Dependency graph (DAG)

- T1 → T2 → T3 → T4 → T5 → T6 → T7

## Execution plan

### Critical path
- T1 → T2 → T3 → T4 → T5 → T6 → T7

### Parallel tracks (lanes)
- Single lane — tasks are strictly sequential due to cascading file dependencies.

## Production safety

- **Production database**: N/A — this module has no database dependencies.
- **Shared resource isolation**: No ports, sockets, or file paths shared with production. Only OpenAI API calls during integration/e2e tests, using Doppler-managed credentials.
- **Migration deliverable**: N/A — no data model changes.

## Definition of Done (DoD)

All items must be true:

- All tasks completed and verified
- Package tests pass: `make check` from `packages/translate_text_bidirectional/`
- Module isolation: no files outside the ALLOWED list were touched
- Public interface matches module spec exactly
- Zero legacy tolerance (no dead code, no deprecated paths)
- No errors are silenced (no swallowed exceptions)
- Module spec unchanged
- Existing `translate_text` package tests remain green (verified by root `make check`)
- Root `make check` passes (all packages including new one)

## Risks + mitigations

- **Risk**: Extending `core/prompts.py` may regress `build_translation_chain` for existing callers.
  - **Mitigation**: New function is additive; existing function signature untouched. Verify existing `translate_text` tests still pass.
- **Risk**: Combined bidirectional prompt may degrade quality in one direction.
  - **Mitigation**: Mirrored hard integration and e2e tests for both NL→RU and RU→NL.
- **Risk**: Model tool choice may be unreliable for direction inference.
  - **Mitigation**: Few-shot examples in prompt teach direction selection explicitly.

## Migration plan (if data model changes)

N/A — no data model changes.

## Rollback / recovery notes

- Revert all commits in this sprint branch. Core extension is additive and backward-compatible.

## Task validation status

- Per-task validation order: `T1` → `T2` → `T3` → `T4` → `T5` → `T6` → `T7`
- Validator: self-validated
- Outcome: approved
- Notes: All tasks checked against checklists A–G

## Sources used

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md`
- Reference service: `packages/translate_text/src/nl_processing/translate_text/service.py`
- Reference tests: `packages/translate_text/tests/` (all files)
- Reference prompt generator: `packages/translate_text/src/nl_processing/translate_text/prompts/generate_nl_ru_prompt.py`
- Core prompts: `packages/core/src/nl_processing/core/prompts.py`
- Core exceptions: `packages/core/src/nl_processing/core/exceptions.py`
- Core models: `packages/core/src/nl_processing/core/models.py`
- Reference pyproject: `packages/translate_text/pyproject.toml`
- Reference Makefile: `packages/translate_text/Makefile`
- Root pyproject: `pyproject.toml`
- Root Makefile: `Makefile`
- Root ruff config: `ruff.toml`

## Contract summary

### What (requirements)
- Bidirectional NL<->RU text translator with model-inferred direction
- Two direction-specific tools, model-decided tool choice
- One combined prompt asset
- Same quality bar as `translate_text` (markdown preservation, no chatter, performance)

### How (architecture)
- Extend `core/prompts.py` with `build_bidirectional_translation_chain` (multi-tool, no forced choice)
- New package with `BidirectionalTextTranslator` service class
- Prompt generator script producing serialized LangChain prompt JSON
- Test suite mirroring `translate_text` patterns in both directions

## Impact inventory (implementation-facing)

- **Module**: `translate_text_bidirectional` at `packages/translate_text_bidirectional/`
- **Interfaces**: `BidirectionalTextTranslator.__init__()`, `BidirectionalTextTranslator.translate()`
- **Data model**: None
- **External services**: OpenAI API (via LangChain ChatOpenAI)
- **Test directory**: `packages/translate_text_bidirectional/tests/`
