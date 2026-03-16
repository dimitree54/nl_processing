---
title: "packages/core baseline green-check repair"
document_type: "task"
module: "packages/core"
status: "done"
---

# Task: Restore `packages/core` baseline green state

## Problem Statement

`packages/core` must be brought back to a fully green baseline before the planned protocol/model refactor starts. The current package-level quality gate is `make check`, and `packages/core/Makefile` defines that gate as `lint` followed by `test-unit`.

The currently confirmed blocking failure is Ruff rule `TID251` (`typing.Any` is banned) in `packages/core/src/nl_processing/core/detail_ports.py`. During repo review, there is also an obvious broken public import surface in `packages/core/src/nl_processing/core/ports.py`, which imports `nl_processing.core.tiered_ports` even though that module is not present in `packages/core/src/nl_processing/core/`.

There is also a documentation contradiction that must guide this prerequisite repair: `packages/core/docs/module-spec.md` documents only `nl_processing.core.protocols.ScoredPairProvider` as the shared protocol contract, while `packages/core/src/nl_processing/core/ports.py` currently re-exports undocumented detail/tiered/progress port surfaces, some of which are partly missing in source.

This task is a narrow prerequisite cleanup only: restore a clean baseline with the smallest proper source/test fix set required for `make check` to pass, and stop there.

## Why This Exists

- The larger protocol/domain redesign should begin from a known-green baseline, not while existing lint/import breakage is still present.
- The package already has documented fail-fast and no-`Any` rules in `packages/core/docs/module-spec.md` and `packages/core/ruff.toml`; this cleanup brings implementation back into compliance.
- Fixing baseline check failures now reduces ambiguity about which failures belong to the upcoming refactor versus pre-existing package debt.

## Relevant Context To Read First

### Repo / module docs

- `README.md`
- `packages/core/docs/module-spec.md`
- `packages/core/Makefile`
- `packages/core/ruff.toml`

### Source files directly involved in the current failure surface

- `packages/core/src/nl_processing/core/detail_ports.py`
- `packages/core/src/nl_processing/core/ports.py`
- `packages/core/src/nl_processing/core/progress_ports.py`
- `packages/core/src/nl_processing/core/protocols.py`
- Any additional `packages/core/src/nl_processing/core/*.py` files directly implicated by newly uncovered `make check` failures

## Pre-Implementation Research Results

These findings are already established and should be treated as fixed starting context for the repair:

- `packages/core/src/nl_processing/core/tiered_ports.py` does not exist in source.
- `packages/core/docs/module-spec.md` does not document `tiered_ports` or any tiered port contract.
- `packages/core/src/nl_processing/core/detail_models.py` does not exist in source.
- `packages/core/src/nl_processing/core/detail_ports.py` imports `DetailedWordRecord` from missing module `nl_processing.core.detail_models` and also uses banned `typing.Any`.
- `packages/core/src/nl_processing/core/ports.py` re-exports detail-related and tiered-related ports even though the tiered module is missing and the detail surface is not supported by a present `detail_models.py` file.
- `packages/core/src/nl_processing/core/progress_ports.py` contains real source definitions for `RemoteProgressSyncPort` and `RemoteDeletePort`, but those progress ports are not documented in `packages/core/docs/module-spec.md`.
- The narrow prerequisite task must follow the docs-driven repo rule: do not invent new undocumented protocol/model source files just to preserve a broken re-export surface.

### Tests to use when validating repair scope

- `packages/core/tests/unit/core/test_protocols.py`
- Any additional files under `packages/core/tests/unit/` that fail after source repair work begins

## Relevant Skills

- No specialized external skill is required for implementation.
- Do not expand this work into a spec rewrite or feature workflow; this is a package-baseline repair task only.

## Scope

### In Scope

- Remove the banned `typing.Any` usage that currently fails Ruff in `packages/core/src/nl_processing/core/detail_ports.py`.
- Repair the broken public import surface in `packages/core/src/nl_processing/core/ports.py` so imports resolve against real package contents and stop exposing obviously broken undocumented surfaces.
- Run `make check` in `packages/core` iteratively and fix any additional source/test issues that are directly uncovered while restoring green state.
- Make the minimum coherent implementation/test changes needed to satisfy the existing documented contracts and current package checks.
- Prefer contraction of broken undocumented re-export surface over creating new undocumented modules or starting protocol redesign.

### Out of Scope

- The larger protocol redesign.
- Model redesign.
- Domain contract changes beyond what is strictly required to restore the existing baseline.
- New features, new abstractions, or cross-package architectural cleanup.
- Creating new undocumented source modules such as `packages/core/src/nl_processing/core/detail_models.py` or `packages/core/src/nl_processing/core/tiered_ports.py`.
- Expanding `packages/core/docs/module-spec.md` or other docs to bless currently undocumented port surfaces.
- Changes outside `packages/core`.
- Any documentation updates other than this task file; all other docs are explicitly out of scope for this prerequisite repair.

## Dependencies

### Code / config dependencies

- `packages/core/Makefile` defines the required completion gate: `lint` + `test-unit`.
- `packages/core/ruff.toml` bans `typing.Any` via `TID251` and enforces the current lint policy.
- `packages/core/docs/module-spec.md` documents fail-fast behavior and explicitly states that `Any` is not allowed in this package.

### Runtime / tool dependencies

- `uv` for environment sync and command execution.
- Ruff, pylint, vulture, jscpd, and pytest as invoked by `make check`.

## Explicit File Scope Expectations For Implementation

Implementation is expected to touch only the smallest set of files required to restore green checks inside `packages/core`.

Expected primary file scope:

- `packages/core/src/nl_processing/core/detail_ports.py`
- `packages/core/src/nl_processing/core/ports.py`

Conditionally allowed only if `make check` exposes additional failures after those fixes:

- Other files under `packages/core/src/nl_processing/core/`
- Existing tests under `packages/core/tests/unit/`

Not allowed:

- Any file outside `packages/core`
- Any docs except this task file
- New source files to recreate undocumented missing model/port modules
- Package config churn unless an existing `make check` failure proves it is strictly required

## Intended Repair Direction

This prerequisite repair should restore green checks without inventing undocumented new source modules.

Preferred direction:

- Remove broken re-exports/imports of non-existent modules from `packages/core/src/nl_processing/core/ports.py`.
- Treat undocumented detail/tiered port surfaces as non-baseline for this task unless an existing documented source/test contract proves otherwise.
- Avoid creating `detail_models.py`, `tiered_ports.py`, or any substitute placeholder modules.
- Avoid redesigning protocol ownership or expanding the module spec during this repair.

Safe handling of the `Any`-typed detail protocols:

- First preference: if the detail port surface is not required by the current documented baseline and is only contributing broken/undocumented imports, remove it from the public re-export surface in `ports.py`.
- If `detail_ports.py` must remain in source for package-local reasons, replace `Any` only with a concrete, already-supported type that can be justified from existing source/tests/docs.
- If no concrete type can be justified without inventing a missing detail model contract, do not guess; escalate instead of fabricating a new payload schema.

## Pre-Implementation Decision Checklist

The implementer should confirm these decisions before changing source:

- Confirm `packages/core/docs/module-spec.md` still documents `nl_processing.core.protocols.ScoredPairProvider` as the only shared protocol contract relevant to this repair.
- Confirm `packages/core/src/nl_processing/core/tiered_ports.py` and `packages/core/src/nl_processing/core/detail_models.py` are still absent.
- Confirm there is no existing unit-test coverage or documented contract that requires preserving the broken `ports.py` re-exports for tiered/detail surfaces.
- Prefer removing broken undocumented re-exports from `ports.py` instead of reconstructing missing modules.
- Do not create new files to satisfy imports unless the user explicitly broadens scope.
- If `detail_ports.py` cannot be made compliant without guessing undocumented contracts, escalate instead of introducing speculative typing or model definitions.

## Implementation Plan

1. Reproduce the current package failure by running `make check` in `packages/core` and capture the first failing gate.
2. Verify that the missing `tiered_ports.py` and `detail_models.py` surfaces are still absent and remain undocumented in `packages/core/docs/module-spec.md`.
3. Repair `packages/core/src/nl_processing/core/ports.py` first so its public re-export surface references only real, defensible baseline surfaces and no longer imports missing undocumented modules.
4. Reassess whether `packages/core/src/nl_processing/core/detail_ports.py` still needs source-level repair after the broken public re-export surface is removed.
5. If `detail_ports.py` still participates in `make check`, remove the banned `Any` only through a concrete type justified by existing source/tests/docs; otherwise escalate rather than guessing a new contract.
6. Re-run `make check`.
7. For each newly exposed failure, apply the smallest proper fix that restores the current baseline without introducing protocol/model redesign work.
8. Continue until the full `make check` command is 100% green.

## Constraints And Decision Rules

- Prefer concrete typing over permissive placeholders; do not replace `Any` with another vague top type unless the package already documents that exact contract.
- Preserve current public behavior unless a check failure proves it is already broken.
- Prefer removing broken undocumented exports over preserving them through speculative new modules or guessed contracts.
- Do not invent the later refactor early; if a fix would require redesigning protocols, models, or package boundaries, stop and escalate rather than expanding scope.
- Follow existing package style and fail-fast rules.
- Keep fixes minimal, but do not use hacks, ignores, or linter suppression to make checks pass.

## Acceptance Criteria

- `make check` in `packages/core` completes successfully with no failing lint or unit-test steps.
- `typing.Any` is fully removed from the current failing usage in `packages/core/src/nl_processing/core/detail_ports.py`.
- The public import surface in `packages/core/src/nl_processing/core/ports.py` no longer references missing modules or undocumented broken re-export surfaces.
- Any additional failures uncovered while restoring green state are fixed within the same narrow baseline-repair effort.
- No work from the upcoming protocol/model redesign is pulled into this task.
- Repo code style and existing package conventions are preserved.
- All touched package checks and auto-quality gates are green unless a pre-existing contradiction is discovered and explicitly reported.
- No new undocumented source modules are created to satisfy missing imports.

## Validation Gates

- Run `make check` in `packages/core`; this is the required end-state gate.
- Treat `lint` and `test-unit` as equally required because `packages/core/Makefile` defines `check` as both.
- Validate that Ruff no longer reports `TID251` for `detail_ports.py`.
- Validate that package imports exercised by lint/tests no longer fail because of the broken `ports.py` re-export surface.

## Test Expectations

- Existing unit tests in `packages/core/tests/unit/` remain green.
- If new failures appear only after the lint/import repairs, update or add the minimal package-local unit coverage needed to keep the repaired baseline stable.
- Linter, duplication, and other automated quality checks invoked by `make check` must all pass.

## Risks

- The missing `tiered_ports` import may indicate partially deleted or partially migrated protocol work; a naive fix could accidentally remove a surface that some unpublished consumer expected.
- Replacing `Any` may expose undocumented payload-shape assumptions that cannot be resolved safely from current source/docs.
- Additional hidden failures may appear only after the first Ruff issue is fixed, which can slightly expand the repair set.

## Blockers / Escalation Conditions

- If restoring green state requires changes outside `packages/core`, stop and report the cross-module dependency instead of proceeding.
- If the only viable fix requires protocol or model redesign rather than baseline repair, stop and report that the prerequisite task is underspecified for the actual breakage.
- If implementation reveals that preserving green state requires inventing `detail_models.py`, `tiered_ports.py`, or any other undocumented module, stop and escalate; that is outside scope.
- If implementation reveals a contradiction between `packages/core/docs/module-spec.md` and the required green-state fix, stop and report the contradiction before changing behavior.
- If `detail_ports.py` cannot be made compliant without guessing undocumented payload/model contracts, stop and ask for user direction rather than inventing a replacement schema.
- If existing tests or external consumers are discovered to rely on undocumented progress/detail/tiered ports, stop and escalate because that would require a documentation/ownership decision, not just baseline repair.

## Done Definition

This task is done only when `packages/core` is back to a fully green `make check` baseline and the repair remains tightly limited to pre-refactor cleanup.
