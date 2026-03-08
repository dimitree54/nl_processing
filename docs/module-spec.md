---
title: "nl_processing Module Spec"
module_name: "nl_processing"
document_type: "module-spec"
related_docs:
  - "docs/ENV_VARS.md"
  - "docs/REALEASE_WORKFLOW.md"
---

# Module Spec: nl_processing

## 1. Module Snapshot

### Summary

`nl_processing` is a multi-package Python repository and aggregate distribution for Dutch-language processing workflows. The root module owns the published aggregate package, repository-wide quality gates, and shared documentation conventions, while day-to-day implementation work happens inside package-local module boundaries. The main workflow remains image extraction -> word extraction -> translation -> persistence/cache -> sampling, with cross-package DTOs and behavioral ports centralized in `core`.

### System Context

The root project sits above the package modules under `packages/` and defines how they are assembled, tested, and documented together. It exposes the published `nl_processing` aggregate package, repo-wide `make check` automation, and shared constraints such as explicit cross-package dependencies and package-local test ownership.

### In Scope

- Aggregate packaging of the published `nl_processing` distribution from the repository root.
- Repository-wide automation, shared docs, and package index/navigation.
- Shared structural rules for package layout, imports, and quality gates.
- Canonical references to package-level module specs and operational docs.

### Out of Scope

- Package-specific runtime behavior, prompts, and domain logic.
- Package-internal schemas, APIs, or storage contracts beyond shared rules.
- Per-module implementation details already documented inside package docs.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Package-local development remains the primary engineering boundary. | Needs Review | Reflected by per-package `pyproject.toml`, `ruff.toml`, `pytest.ini`, `tests/`, and `docs/`. |
| A-2 | The published root package continues bundling the current package set from `packages/`. | Needs Review | Root `pyproject.toml` explicitly enumerates package mappings. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The root project must publish an aggregate `nl_processing` package that exposes the package modules through the public `nl_processing.*` import path. | Must | Implemented by root `pyproject.toml` package mappings. |
| FR-2 | Every independently developed module must live under `packages/<module>` and keep package-local config, tests, and docs. | Must | Shared repo invariant. |
| FR-3 | Cross-package dependencies must be explicit in the consuming package metadata rather than relying on the root layout. | Must | Prevents hidden coupling. |
| FR-4 | The repository must expose one repo-wide quality entrypoint that runs shared static checks and package-level tests. | Must | Provided by the root `Makefile`. |
| FR-5 | Shared documentation must point to one canonical module-spec document per module and one root module-spec for repo-wide rules. | Must | This migration makes `module-spec.md` the canonical format. |

### Rules and Invariants

- BR-1: The root project is orchestration and aggregate packaging, not the primary implementation boundary.
- BR-2: Shared DTOs, cross-package behavioral ports, exceptions, and prompt helpers belong in `core`, not in package-specific modules.
- BR-3: Package-local tests remain in the owning package; no shared root `tests/` tree is reintroduced.
- BR-4: Optional orchestration behavior across modules should be composed by callers or dependency injection rather than hidden inside foundational packages.
- BR-5: When multiple modules need the same storage or sync behavior, the reusable contract belongs in `core`; concrete packages remain implementations of that contract.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Root and package projects must target Python 3.12+. | `requires-python >=3.12` | Defined in root and package metadata. |
| NFR-2 | Maintainability | Package-local development must be practical without editing root-only configs. | Per-package config files required | Keeps package work isolated. |
| NFR-3 | Quality | Repo-wide automation must cover static analysis plus package-local test gates. | `make check` must remain green | Current root automation runs vulture, jscpd, and per-package checks. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | A new package is added without root packaging metadata or docs links. | Aggregate build or docs navigation becomes incomplete. | Update root `pyproject.toml`, README, and root module spec together. |
| FM-2 | A package depends on another package implicitly. | Local package execution becomes fragile or environment-dependent. | Fail review and add the dependency explicitly to the consumer package metadata. |
| FM-3 | Package-local docs drift away from the root docs model. | Developers lose a canonical navigation path. | Keep README and package `docs/module-spec.md` links in sync during module changes. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Aggregate build metadata and package mappings.
- Repository-wide docs index and shared operational docs.
- Shared quality entrypoints (`make check`, package-check orchestration).

**Does Not Own:**

- Package-specific product behavior.
- Package-local prompts, fixtures, or runtime settings.
- Package-internal storage, models, or service APIs beyond shared rules.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Build | Outbound | Python packaging toolchain | Root `pyproject.toml` exports aggregate `nl_processing` package mappings. | Canonical root packaging interface. |
| IF-2 | Automation | Inbound | Repository contributors / CI | `make check` runs repo-wide checks and package-local test targets. | Primary shared quality entrypoint. |
| IF-3 | Documentation | Outbound | Developers | Root docs point to package module specs plus env/release docs. | Canonical navigation layer. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Root `pyproject.toml` | Owned | Aggregate build metadata and package mappings. | Versioned with the repo | Must stay aligned with `packages/`. |
| Root `Makefile` | Owned | Repo-wide quality automation. | Versioned with the repo | Delegates to package-local checks. |
| Root docs | Owned | Repo-wide conventions and canonical module-spec index. | Versioned with the repo | Includes env var and release docs. |
| `uv.lock` / tool metadata | Owned | Shared dependency lock and tooling baseline. | Versioned with the repo | Supports reproducible development. |

### Processing Flow

1. A contributor works in one package under `packages/<module>`.
2. Package-local code, tests, and docs are updated within that package boundary.
3. The root `Makefile` orchestrates repo-wide static checks and package test runs.
4. The root aggregate package and docs expose the repository as one publishable toolkit.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep one repository with per-package projects. | Decided | Preserves shared docs/CI while keeping module work isolated. | Every module must retain its own config, tests, and docs. |
| DEC-2 | Keep `core` as the shared contract package for DTOs, behavioral ports, exceptions, and prompt helpers. | Decided | Prevents ad hoc cross-package coupling. | Shared types and narrow multi-module protocols should move to `core` before new direct package dependencies are introduced. |
| DEC-3 | Treat the root project as aggregate/orchestration, not the primary development boundary. | Decided | Keeps developer workflows focused on the owning package. | Root docs and automation summarize package boundaries instead of replacing them. |
| DEC-4 | Keep storage composition protocol-first at package boundaries. | Decided | Shared consumers such as `sampling` and `database_cache` should type against `core` contracts instead of concrete storage classes. | Concrete modules can still provide defaults without owning the shared interface layer. |

### Consistency Rules

- CR-1: New modules must follow the same package layout and docs structure as existing packages.
- CR-2: Any root-level docs change that alters canonical paths must update README links in the same change.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-1 | IF-1, DEC-1, DEC-3 | QA-1 |
| FR-4 | IF-2, DEC-3, CR-1 | QA-2 |
| FR-5 | IF-3, CR-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: The root docs expose one canonical `docs/module-spec.md` plus one `module-spec.md` inside each module docs directory.
- AC-2: README points to the canonical module specs and retains links to shared operational docs.
- AC-3: The root build metadata still enumerates the aggregate package mappings for the current modules.

### Testing Strategy

**Framework and Constraints:**

- Reuse the existing package-local `pytest` structure and the root `Makefile`.
- Keep the root check focused on orchestration and shared static analysis, not package-specific test duplication.

**Unit:**

- N/A at the root level; unit tests remain package-local.

**Integration:**

- Validate that package-local commands still run from inside each package.

**Contract:**

- Verify that root packaging metadata and README links reflect the actual package set and docs locations.

**E2E or UI Workflow:**

- Manual repo navigation: a developer can move from README to the root spec and then into package module specs without dead links.

**Operational or Non-Functional:**

- `make check` remains the canonical repo-wide quality gate.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-1 | Operational | Root packaging and import path validation via aggregate build/test flow | Release / PR CI | Confirms root package mappings stay valid. |
| QA-2 | FR-4 | Operational | `make check` | PR CI | Covers repo-wide static checks and package test gates. |
| QA-3 | FR-5 | Manual | README/docs navigation review after docs migrations | PR review | Fastest way to catch broken doc links. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | `make check` | Enforce repo-wide quality and package-local checks. | PR CI | Static analysis or package test failures. |
| SC-2 | README/doc link review | Keep canonical docs paths accurate after module changes. | PR review | Dead or stale docs paths. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Docs navigation | Link accuracy across markdown docs is only partially covered by tooling. | Open README, follow the root spec link, then open package specs from the module table. | Working links and correct files. |
| Aggregate install workflow | The root package is an orchestration artifact spanning many subpackages. | Install from the root in a clean environment and import key modules. | Successful install/import output. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Root package mappings drift from the actual package layout. | Broken aggregate builds or missing modules in releases. | Update root `pyproject.toml` whenever module packages are added or moved. |
| RISK-2 | A future module is added without the canonical `module-spec.md` pattern. | Documentation becomes inconsistent again. | Treat the module-spec format as a repo-level docs requirement in reviews. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the aggregate root package and the package modules continue sharing the same version number, or diverge over time? | Open | Project owner to decide before the next packaging change | The current repo uses aligned versions. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending packaging strategy review | Decide during the next release-process update |

### Deferred Work

- D-1: Introduce automated markdown link checking if docs volume continues to grow.
- D-2: Revisit aggregate/package versioning strategy when new modules or external consumers are added.
