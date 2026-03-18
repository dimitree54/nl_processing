---
title: "database_core Module Spec"
module_name: "database_core"
document_type: "module-spec"
related_docs:
  - "../../database/docs/module-spec.md"
  - "../../../docs/module-spec.md"
---

# Module Spec: database_core

> This spec describes the module's desired target-state behavior and public contract.
> It defines WHAT the module must do, not HOW it is implemented.

## 1. Module Snapshot

### Summary

`database_core` owns provider-facing database mechanics shared by higher-level persistence modules. It provides the abstract backend contract, default Neon PostgreSQL implementation, backend configuration helpers, SQL/table bootstrap helpers, and generic database failure types. It must stay unaware of the application domain surface exposed by `database` service/store APIs.

### System Context

`database_core` sits below `database` and any future persistence modules that need the same backend/provider foundation. It depends on shared enums from `core`, but it does not own public word-service, detailed-store, or progress-store workflows.

### In Scope

- Backend/provider contract and connection lifecycle.
- Default Neon PostgreSQL backend implementation.
- Generic database configuration helpers.
- Generic database/provider exceptions.
- SQL bootstrap and query helpers used by the backend.

### Out of Scope

- Domain service APIs such as `DatabaseService`, `DetailedWordStore`, and progress stores.
- Domain DTOs and business-level validation rules.
- Cache logic, sampling logic, and translator/extractor orchestration.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | Neon PostgreSQL remains the default production backend. | Approved | Current extraction scope keeps Neon as the only concrete provider. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | Expose `AbstractBackend` as the supported backend contract for higher-level persistence modules. | Must | Provider boundary. |
| FR-2 | Expose `NeonBackend(database_url)` as the default concrete backend implementation. | Must | Default remote provider. |
| FR-3 | Expose `read_database_url()` and fail fast when `DATABASE_URL` is missing. | Must | Shared backend initialization helper. |
| FR-4 | Expose a backend contract that can safely create independent backend handles for background work while keeping provider failures explicit. | Must | Higher-level modules rely on this to avoid connection reuse across background tasks. |
| FR-5 | Surface provider/connection/query failures as `DatabaseError` and misconfiguration as `ConfigurationError`. | Must | Shared failure contract. |
| FR-6 | Create required remote tables idempotently for the backend-supported schema helpers. | Must | Backend bootstrap contract. |

### Rules and Invariants

- BR-1: `database_core` must not expose application-specific service/store APIs.
- BR-2: Missing `DATABASE_URL` must fail immediately and explicitly.
- BR-3: Backend operations stay async.
- BR-4: Neon remains the default backend when no explicit backend is injected.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Compatibility | Python runtime compatibility | `>=3.12` | Package requirement. |
| NFR-2 | Reliability | Provider failures must be surfaced without fallback behavior. | Fail fast | Repo-wide rule. |
| NFR-3 | Code quality | Python modules must stay within repo file-size limits. | `pylint --max-module-lines=200` | Enforced by package checks. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Notes |
| --- | --- | --- | --- |
| FM-1 | `DATABASE_URL` missing | Raise `ConfigurationError` | Caller must configure env correctly. |
| FM-2 | Connection or query fails | Raise `DatabaseError` | No silent retry/fallback. |

## 3. Public Contract

### Responsibilities and Boundaries

**Responsible For:**

- Backend/provider abstractions.
- Backend connection/bootstrap mechanics.
- Generic database/provider error types.

**Not Responsible For:**

- Application-domain service/store contracts.
- Domain DTO shaping and business workflows.

### Public Interfaces

| ID | Interface Type | Direction | Counterparty | Contract Summary | Expected Behavior |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Outbound | `database` and future persistence modules | `AbstractBackend` | Defines supported async backend operations. |
| IF-2 | Python API | Outbound | `database` and tests | `NeonBackend` | Provides default Neon implementation. |
| IF-3 | Python API | Outbound | `database` and future persistence modules | `read_database_url()` plus `AbstractBackend.create_background_backend()` | Supplies fail-fast configuration and backend cloning for concurrent/background usage. |
| IF-4 | Python API | Outbound | Callers and tests | `ConfigurationError`, `DatabaseError` | Shared generic database error types. |

### Internal and Non-Contract Notes

- SQL helper modules under `nl_processing.database_core.backend` are internal implementation helpers; callers should not depend on them as stable public API.
- Package-local test helpers live under `packages/database_core/tests/` and are not part of the supported runtime contract.

### External Dependencies and Constraints

| ID | Dependency or Constraint | Why It Matters | Behavioral Assumption or Limit | Notes |
| --- | --- | --- | --- | --- |
| EC-1 | Neon PostgreSQL via `asyncpg` | Default remote provider | Current extraction supports one concrete provider | Additional providers are future additive work. |

### Cross-Module Change References

| Affected Module | Why It Must Change | External Spec or Doc Reference | Ownership Status |
| --- | --- | --- | --- |
| `database` | It now consumes provider/core mechanics from `database_core` instead of owning them directly | `../../database/docs/module-spec.md` | Updated |

## 4. Acceptance and Validation

### Acceptance Criteria

- AC-1: Higher-level persistence modules use `database_core` directly for provider configuration, backend abstractions, and concrete Neon integration without any compatibility import layer.
- AC-2: `database_core` owns the abstract backend, Neon backend, generic DB configuration helpers, and generic DB exceptions.
- AC-3: Backend-focused unit and integration tests run from `database_core` without relying on `database` internals or `database`-owned test helpers.

### High-Level Validation Coverage

| ID | Target | What Must Be True | Observable Evidence or Result |
| --- | --- | --- | --- |
| VAL-1 | FR-1, FR-2 | Higher-level modules can construct and use the backend contract and Neon implementation, including safe background backend cloning | Unit/integration tests pass via `database_core` package paths |
| VAL-2 | FR-3, FR-5 | Missing env and provider failures remain explicit | Config and backend tests still raise documented exceptions |
| VAL-3 | AC-3 | Package-local tests no longer depend on `database` runtime or `database` test helpers | `database_core` tests import only `database_core`-owned helpers or direct backend APIs |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | Some backend abstractions still carry domain-shaped method names and table conventions | `database_core` is not fully domain-neutral yet | Keep this extraction focused on provider/core ownership first; refine interfaces later |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | Should the backend contract be further decomposed into smaller provider-neutral ports later? | Open | Future refactor | Out of scope for the first extraction step |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Approved | Kept as explicit constraint | EC-1 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-2 | OQ-1 | Unresolved | Keep as follow-up refactor work | Deferred |

### Deferred Work

- D-1: Further split the backend contract into smaller provider-neutral ports after the first extraction stabilizes.
