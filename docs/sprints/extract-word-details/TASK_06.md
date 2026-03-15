---
Task ID: T6
Title: Update root configs + final cross-module validation
Sprint: 2026-03-13_extract-word-details
Module: extract_word_details, database, database_cache (root configs only)
Depends on: T1, T2, T3, T4, T5
Parallelizable: no (final validation)
---

## Goal / value

After this task, the root `Makefile`, `pyproject.toml`, and `ruff.toml` are updated to include `extract_word_details`, and the full `make check` passes across all three affected packages. The sprint is complete: all three module specs are fully in sync with their implementations.

## Context (contract mapping)

- Root `Makefile`: `PACKAGES` list must include `extract_word_details`
- Root `pyproject.toml`: `[tool.setuptools]` packages and `[tool.setuptools.package-dir]` must include `extract_word_details` and its `prompts` subpackage
- Root `ruff.toml`: `src` list must include the new package path
- Module specs: `packages/extract_word_details/docs/module-spec.md`, `packages/database/docs/module-spec.md`, `packages/database_cache/docs/module-spec.md` — final alignment check

## Preconditions

- T1–T5 all complete
- `make check` passes individually in `packages/extract_word_details/`, `packages/database/`, and `packages/database_cache/`

## Non-goals

- Implementing any new features or fixing bugs (those belong in T1–T5)
- Running the global `make check` for ALL packages (only verify the three affected ones + root-level checks)
- Modifying any module spec docs

## Module boundary constraints (STRICTLY ENFORCED)

**ALLOWED — this task may ONLY touch:**

- Root `Makefile` — add `extract_word_details` to `PACKAGES` list
- Root `pyproject.toml` — add package registration
- Root `ruff.toml` — add src path

**FORBIDDEN — this task must NEVER touch:**

- Any source code in any package (T1–T5 own all source code changes)
- Module spec docs
- Any package-level configs (those were handled in T1–T5)

**Test scope:**

- Run `make check` in each of the three affected packages to verify
- Run root `make check` to verify full monorepo integration (optional, for validation)

## Touched surface (expected files / modules)

**Files to modify:**

- `Makefile` (root) — add `extract_word_details` to `PACKAGES` list
- `pyproject.toml` (root) — add `extract_word_details` entries to `[tool.setuptools]` and `[tool.setuptools.package-dir]` and `[tool.setuptools.package-data]`
- `ruff.toml` (root) — add `packages/extract_word_details/src` to `src` list

## Dependencies and sequencing notes

- This is the final task. All other tasks must be complete.
- If any prior task left incomplete work, this task blocks until it's resolved.

## Third-party / library research (mandatory for any external dependency)

- No new libraries. This task only modifies config files.

## Implementation steps (developer-facing)

1. **Update root `Makefile`**:
   - Add `extract_word_details` to the `PACKAGES` list.
   - Current: `PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_text_bidirectional translate_text_from_image translate_word database database_cache sampling`
   - New: `PACKAGES = core extract_text_from_image extract_words_from_text translate_text translate_text_bidirectional translate_text_from_image translate_word extract_word_details database database_cache sampling`
   - **Important**: `extract_word_details` must appear BEFORE `database` in the list because `database` tests may depend on `extract_word_details` being checked first (package ordering matters for `make check` serial execution). Actually, the root `make check` runs each package independently via `make -C packages/$$pkg check`, so ordering only matters for sequential execution. Place `extract_word_details` after `translate_word` and before `database` to match the dependency order.

2. **Update root `pyproject.toml`**:
   - Add to `[tool.setuptools]` packages list:
     ```
     "nl_processing.extract_word_details",
     "nl_processing.extract_word_details.models",
     "nl_processing.extract_word_details.prompts",
     ```
   - Add to `[tool.setuptools.package-dir]`:
     ```
     "nl_processing.extract_word_details" = "packages/extract_word_details/src/nl_processing/extract_word_details"
     "nl_processing.extract_word_details.models" = "packages/extract_word_details/src/nl_processing/extract_word_details/models"
     "nl_processing.extract_word_details.prompts" = "packages/extract_word_details/src/nl_processing/extract_word_details/prompts"
     ```
   - Add to `[tool.setuptools.package-data]`:
     ```
     "nl_processing.extract_word_details.prompts" = ["*.json"]
     ```

3. **Update root `ruff.toml`**:
   - Add `"packages/extract_word_details/src"` to the `src` list.

4. **Validate: run `make check` in each affected package**:
   - `make check` in `packages/extract_word_details/` — all tests pass
   - `make check` in `packages/database/` — all tests pass (existing + new from T4)
   - `make check` in `packages/database_cache/` — all tests pass (existing + new from T5)

5. **Cross-module validation** — manually verify:
   - `WordDetailsExtractor.extract()` returns `list[DetailedWordRecord]` matching the `DetailedWordExtractorPort` protocol
   - `DetailedWordStore` can accept a `WordDetailsExtractor` instance as its `extractor` parameter
   - `DetailedWordCacheService` can accept a `DetailedWordStore` instance as its `remote_store` parameter
   - Schema keys and versions are consistent across all three modules
   - The `create_tables()` flow creates the `word_details_nl_ru` table

6. **Final spec alignment check** — read each module spec and verify:
   - Every FR in `extract_word_details` spec (FR-1..FR-11) is implemented
   - Every FR in `database` spec (FR-11..FR-14) is implemented
   - Every FR in `database_cache` spec (FR-11..FR-15) is implemented
   - No implemented behavior contradicts the specs
   - Log any discrepancies as issues for the user (do NOT modify specs)

## Production safety constraints (mandatory)

- **No production impact**: This task only modifies root config files. No code execution, no database operations.

## Anti-disaster constraints (mandatory)

- **Reuse before build**: Only config modifications — no new code.
- **Correct file locations**: Root configs only.
- **No regressions**: Existing packages in the `PACKAGES` list must still pass `make check`.

## Error handling + correctness rules (mandatory)

- Not applicable — config changes only.

## Zero legacy tolerance rule (mandatory)

- The root configs must be up to date with the new package. No stale entries.

## Acceptance criteria (testable)

1. Root `Makefile` `PACKAGES` list includes `extract_word_details`.
2. Root `pyproject.toml` registers `nl_processing.extract_word_details`, its `models` subpackage, and its `prompts` subpackage.
3. Root `ruff.toml` `src` list includes `packages/extract_word_details/src`.
4. `make check` passes in `packages/extract_word_details/`.
5. `make check` passes in `packages/database/`.
6. `make check` passes in `packages/database_cache/`.
7. All FRs from all three module specs are implemented and verified.
8. No spec discrepancies found (or discrepancies are logged for user).

## Verification / quality gates

- [x] Root Makefile updated
- [x] Root pyproject.toml updated
- [x] Root ruff.toml updated
- [x] `make check` passes in all three affected packages
- [x] Cross-module interface compatibility verified
- [x] Spec alignment verified for all three modules

## Edge cases

- Root `Makefile` ordering: `extract_word_details` before `database` to match dependency order
- Root `pyproject.toml` must include the `models` and `prompts` subpackages separately (same pattern as `translate_word.prompts`)
- If the `extract_word_details` package has additional subpackages (beyond `models` and `prompts`), they must also be registered

## Notes / risks

- **This task is a validation gate, not an implementation task.** If any prior task left issues, this task will surface them. The dev should fix issues in the relevant package, not in root configs.
- **Root `make check`** runs each package's `make check` in sequence. Each package check owns its own `vulture`, `jscpd`, lint, and test gates. Running the full root `make check` is the ultimate validation but may take significant time. The dev can run it as a final gate.
