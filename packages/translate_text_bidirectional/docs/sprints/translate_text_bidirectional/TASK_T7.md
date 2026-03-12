---
Task ID: `T7`
Title: `Monorepo integration and final verification`
Sprint: `2026-03-12_translate-text-bidirectional`
Module: `translate_text_bidirectional`
Depends on: `T6`
Parallelizable: no
Owner: Developer
Status: planned
---

## Goal / value

Integrate `translate_text_bidirectional` into the monorepo root configuration so that the root `make check` discovers and validates the new package alongside all existing packages. Verify that existing packages are unaffected. After this task, the module is fully integrated and the entire monorepo is green.

## Context (contract mapping)

- Module spec: `packages/translate_text_bidirectional/docs/module-spec.md` — SC-2 (repo root checks), SC-4 (existing package compatibility), NFR-4
- Root: `pyproject.toml` — package registry, package-data, package-dir mappings
- Root: `Makefile` — PACKAGES list for `make check` loop
- Root: `ruff.toml` — src paths for import resolution
- Root: `vulture_whitelist.py` — dead code whitelist if needed

## Preconditions

- T1–T6 completed. Package `make check` passes locally.
- All service code, prompt assets, and tests are in place and passing.

## Non-goals

- Writing new service code or tests (completed in T1–T6).
- CI/CD pipeline configuration (assumed to run root `make check`).

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**
- Root `pyproject.toml` — add package entries
- Root `Makefile` — add to PACKAGES list
- Root `ruff.toml` — add src path
- Root `vulture_whitelist.py` — add entries if vulture reports false positives
- `packages/translate_text_bidirectional/` — minor fixes if root check reveals issues

**FORBIDDEN — this task must NEVER touch:**
- `packages/translate_text/` — no changes
- `packages/core/` — no changes (T1 already complete)
- Any other package's source or tests

**Test scope:**
- Test command: `make check` from monorepo root
- Verify all packages pass, including the new one

## Touched surface (expected files / modules)

- Root `pyproject.toml` — 4 new entries
- Root `Makefile` — 1 line change (add to PACKAGES)
- Root `ruff.toml` — 1 new src path
- Root `vulture_whitelist.py` — conditional entries

## Dependencies and sequencing notes

- Depends on T6 (all package-level tests passing).
- This is the final task — no downstream dependencies.

## Third-party / library research (mandatory for any external dependency)

- **Tool**: `vulture` (`>=2.14.0,<3`) — dead code detection. May flag unused imports or variables in the new package.
  - **Documentation**: https://github.com/jendrikseipp/vulture
  - **Known behavior**: Vulture scans `packages/*/src` and `packages/*/tests`. New package code will be included automatically. If Pydantic tool schemas appear unused (they're used via LangChain bind_tools), they need whitelisting.
- **Tool**: `jscpd` — duplicate code detection across packages.
  - **Known behavior**: Shared patterns (conftest.py, test structure) may trigger false positives. Check `.jscpd.json` for existing ignore patterns.

## Implementation steps (developer-facing)

### 1. Update root `pyproject.toml`

Add to `[tool.setuptools]` `packages` list:
```
"nl_processing.translate_text_bidirectional",
"nl_processing.translate_text_bidirectional.prompts",
```

Add to `[tool.setuptools.package-dir]`:
```
"nl_processing.translate_text_bidirectional" = "packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional"
"nl_processing.translate_text_bidirectional.prompts" = "packages/translate_text_bidirectional/src/nl_processing/translate_text_bidirectional/prompts"
```

Add to `[tool.setuptools.package-data]`:
```
"nl_processing.translate_text_bidirectional.prompts" = ["*.json"]
```

### 2. Update root `Makefile`

Add `translate_text_bidirectional` to the PACKAGES variable:
```makefile
PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_text_bidirectional translate_text_from_image translate_word database database_cache sampling
```

### 3. Update root `ruff.toml`

Add to the `src` list:
```toml
"packages/translate_text_bidirectional/src",
```

### 4. Run root `make check`

Execute from the monorepo root. This runs:
- `vulture` across all packages (including new one)
- `jscpd` duplicate code detection
- Per-package `make check` for every package in PACKAGES

### 5. Fix any issues

- **Vulture false positives**: If `_NlToRuTranslation` or `_RuToNlTranslation` Pydantic classes are flagged as unused, add them to `vulture_whitelist.py`:
  ```python
  _NlToRuTranslation  # used by LangChain bind_tools
  _RuToNlTranslation  # used by LangChain bind_tools
  ```
- **jscpd duplicates**: If conftest.py patterns trigger duplicate detection, check if `.jscpd.json` already ignores test fixtures. If not, the test helpers may need minor differentiation or the ignore pattern may need updating.
- **Ruff/pylint issues**: Fix any lint issues revealed by root-level checks that package-level checks missed.

### 6. Verify existing packages

Confirm that all existing packages in PACKAGES still pass their individual `make check`. Specifically verify:
- `packages/translate_text/` — must not regress from T1's core extension.
- `packages/core/` — must pass with the new `build_bidirectional_translation_chain`.

### 7. Final smoke test

Run root `make check` one more time to confirm everything is green.

## Production safety constraints (mandatory)

- No database operations.
- Root config changes are additive — existing packages unaffected.
- No ports or shared resources changed.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Follow exact patterns from existing package entries in root configs.
- **Correct file locations**: Package entries match the actual directory structure.
- **No regressions**: Existing PACKAGES entries unchanged. New entry appended.

## Error handling + correctness rules (mandatory)

- N/A for config changes — no runtime code.

## Zero legacy tolerance rule (mandatory)

- No legacy to remove. Additive integration only.

## Acceptance criteria (testable)

1. Root `pyproject.toml` includes `translate_text_bidirectional` package, prompts sub-package, package-dir mapping, and package-data entry.
2. Root `Makefile` PACKAGES list includes `translate_text_bidirectional`.
3. Root `ruff.toml` src list includes `packages/translate_text_bidirectional/src`.
4. Root `make check` passes completely — all packages green including the new one.
5. `vulture` reports no errors (whitelisting applied if needed).
6. `jscpd` reports no errors (or existing ignore patterns cover expected similarities).
7. Existing `translate_text` package tests still pass.
8. Existing `core` package tests still pass (if any).

## Verification / quality gates

- [ ] Root `make check` passes (all packages)
- [ ] `vulture` clean (no false positives)
- [ ] `jscpd` clean (no unexpected duplicates)
- [ ] All existing packages unaffected
- [ ] New package fully discovered by root tooling
- [ ] No new warnings from any package

## Edge cases

- `vulture` may flag the `_SUPPORTED_PAIRS` constant or Pydantic tool schemas as unused. These are used at runtime via LangChain — whitelist them.
- `jscpd` may flag similarities between `translate_text/conftest.py` and `translate_text_bidirectional/conftest.py`. Both share the `AsyncChainMock` pattern — this is intentional reuse, not harmful duplication. Check `.jscpd.json` for existing ignore rules.

## Notes / risks

- **Risk**: Root `make check` runs all packages sequentially — this can take significant time.
  - **Mitigation**: Run just the new package check first (`make -C packages/translate_text_bidirectional check`), then root check only after package check passes.
- **Risk**: Alphabetical ordering in PACKAGES list may matter for some tools.
  - **Mitigation**: Insert `translate_text_bidirectional` after `translate_text` and before `translate_text_from_image` for natural alphabetical grouping.
