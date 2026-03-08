---
title: "sampling Module Spec"
module_name: "sampling"
document_type: "module-spec"
related_docs:
  - "../../../docs/module-spec.md"
  - "../../database/docs/module-spec.md"
  - "../../database_cache/docs/module-spec.md"
---

# Module Spec: sampling

## 1. Module Snapshot

### Summary

`sampling` selects practice items for a user by sampling translated word pairs with score-aware weighting. It is intentionally stateless: it reads scored pairs from a compatible provider, applies a simple weighting policy, and returns unique `WordPair` results. The module also offers an adversarial helper for multiple-choice distractors based on part-of-speech matching.

### System Context

The module sits on the hot path for practice session generation. By default it reads from `database.ExerciseProgressStore`, but its public dependency boundary is the shared `core.ports.ScoredPairProvider` protocol, so it can accept `database_cache` or any other compatible provider without API changes.

### In Scope

- Public async `WordSampler` with weighted sampling and adversarial distractor helpers.
- Score-aware sampling without replacement.
- Protocol-based scored-store injection.
- Same-part-of-speech adversarial distractor sampling.

### Out of Scope

- Owning progress state or persistence.
- Spaced repetition, decay models, or recent-item suppression.
- Semantic similarity scoring for distractors.
- Multi-language-pair orchestration beyond the configured instance.

### Assumptions

| ID | Assumption | Status | Notes |
| --- | --- | --- | --- |
| A-1 | The simple sign-based weighting policy remains acceptable until a more advanced practice strategy is deliberately introduced. | Needs Review | Current weight rule is positive-score down-weight vs non-positive full weight. |
| A-2 | Candidate retrieval remains delegated to a scored-store dependency rather than being owned by `sampling`. | Needs Review | Keeps the module stateless. |

## 2. Requirements

### Functional Requirements

| ID | Requirement | Priority | Notes |
| --- | --- | --- | --- |
| FR-1 | The module must expose `WordSampler(user_id, source_language, target_language, exercise_types, positive_balance_weight, scored_store?)`. | Must | Current default `positive_balance_weight` is `0.01`. |
| FR-2 | `sample(limit)` must return weighted-sampled `WordPair` results without replacement. | Must | Unique results within one sample call. |
| FR-3 | Weighting must treat non-positive score balances as full weight and positive balances as down-weighted. | Must | Current v1 rule. |
| FR-4 | Multiple `exercise_types` must aggregate by the minimum score across the configured exercises. | Must | Pessimistic aggregation. |
| FR-5 | `sample_adversarial(source_word, limit)` must return same-part-of-speech distractor pairs, exclude the source word, and sample uniformly without replacement. | Must | Multiple-choice helper. |
| FR-6 | The sampler must accept an injected scored-store that implements the shared `core.ports.ScoredPairProvider` contract. | Must | Decouples the module from one concrete backend. |

### Rules and Invariants

- BR-1: `exercise_types` must be a non-empty list.
- BR-2: `positive_balance_weight` must be in `(0, 1]`.
- BR-3: Sampling results contain no duplicates within one call.
- BR-4: Adversarial sampling requires `source_word.language` to match the sampler's configured source language.

### Non-Functional Requirements

| ID | Category | Requirement | Target or Constraint | Notes |
| --- | --- | --- | --- | --- |
| NFR-1 | Performance | Sampling overhead after data retrieval should stay interactive. | Target <200ms for 1k candidates / 50 samples excluding provider latency | Original module target. |
| NFR-2 | Extensibility | Data-source coupling must remain low. | Protocol-based provider injection | Supports `database` and `database_cache`. |
| NFR-3 | Simplicity | The module should stay stateless and easy to reason about. | No owned persistence | All state lives in providers. |

### Failure Modes and Edge Cases

| ID | Scenario | Expected Behavior | Handling or Recovery |
| --- | --- | --- | --- |
| FM-1 | `limit <= 0`. | Return `[]`. | Valid no-op path. |
| FM-2 | No candidates are available from the provider. | Return `[]`. | Caller handles empty practice set. |
| FM-3 | `source_word.language` does not match the configured source language for adversarial sampling. | Raise `ValueError`. | Caller fixes input mismatch. |
| FM-4 | `positive_balance_weight` or `exercise_types` are invalid at construction time. | Raise `ValueError`. | Caller fixes configuration before sampling. |

## 3. Module Design

### Responsibilities and Boundaries

**Owns:**

- Sampling policy and adversarial distractor policy.
- Lightweight validation for sampler configuration and inputs.
- Protocol abstraction for scored-pair providers.

**Does Not Own:**

- Remote or local persistence of words and scores.
- Translation, caching, or user-progress mutation.
- Advanced scheduling or spaced-repetition algorithms.

### Interfaces and Dependencies

| ID | Type | Direction | Counterparty | Contract or Data | Notes |
| --- | --- | --- | --- | --- | --- |
| IF-1 | Python API | Inbound | Callers | `await sample(limit) -> list[WordPair]` | Main practice-set generator. |
| IF-2 | Python API | Inbound | Callers | `await sample_adversarial(source_word, limit) -> list[WordPair]` | Same-POS distractor helper. |
| IF-3 | Protocol | Inbound | `database`, `database_cache`, or mocks | `core.ports.ScoredPairProvider` | Core dependency abstraction. |

### Data and State Ownership

| Entity or State | Ownership | Description | Lifecycle or Retention | Notes |
| --- | --- | --- | --- | --- |
| Sampler configuration | Owned | Exercise types, weight factor, source language, and provider reference. | Runtime only | No persistent state. |
| Candidate scored pairs | Referenced | Input data retrieved from the provider. | Runtime per call | Owned by the provider. |
| Sampled `WordPair` results | Owned | Stateless output of one sampling call. | Runtime per call | Returned directly to callers. |

### Processing Flow

1. The constructor validates `exercise_types` and `positive_balance_weight`, then chooses either the injected provider or the default `ExerciseProgressStore`.
2. `sample(limit)` returns `[]` for non-positive limits, fetches scored pairs, computes weights, and performs weighted sampling without replacement.
3. `sample_adversarial(source_word, limit)` validates language, filters candidates by matching part of speech while excluding the source word, and returns a uniform random subset.
4. Callers consume the resulting `WordPair` list and keep all progress state management outside the module.

### Decisions

| ID | Decision | Status | Rationale | Consequence |
| --- | --- | --- | --- | --- |
| DEC-1 | Keep `sampling` stateless. | Decided | The database or cache modules own score state. | Sampler behavior depends entirely on provider inputs. |
| DEC-2 | Use a simple sign-based weighting rule for v1. | Decided | Easy to explain, test, and ship. | More advanced scheduling remains deferred work. |
| DEC-3 | Aggregate multiple exercises pessimistically via minimum score. | Decided | A word is only down-weighted once it is strong across all requested exercise types. | Mixed-drill sessions remain conservative. |
| DEC-4 | Accept providers through the shared `core` protocol instead of concrete class coupling. | Decided | Enables future hot-path use of `database_cache` without API changes and keeps the protocol owned in one place. | Providers must match the structural contract. |

### Consistency Rules

- CR-1: Sampling methods must remain without-replacement within a single call.
- CR-2: New provider integrations must conform to `ScoredPairProvider` without changing the public sampler API.

### Requirement Traceability

| Requirement | Covered By | Verified By |
| --- | --- | --- |
| FR-2 | IF-1, DEC-1, CR-1 | QA-1 |
| FR-4 | IF-3, DEC-3 | QA-2 |
| FR-6 | IF-3, DEC-4, CR-2 | QA-3 |

## 4. Delivery and Validation

### Acceptance Criteria

- AC-1: Weighted samples return unique `WordPair` values and respect the configured weight policy.
- AC-2: Adversarial samples return only same-part-of-speech distractors, exclude the source word, and validate source-language mismatch.
- AC-3: The sampler works both with the default remote progress store and an injected compatible provider.

### Testing Strategy

**Framework and Constraints:**

- Reuse the existing package-local unit tests and provider mocks.
- Keep the sampler itself free of live API or database dependencies whenever a mock provider is sufficient.

**Unit:**

- Constructor validation, weighting behavior, without-replacement sampling, and adversarial helper behavior.

**Integration:**

- Future integration should validate provider compatibility with real `database` or `database_cache` data if hot-path usage expands.

**Contract:**

- Verify that mock stores and `DatabaseCacheService` satisfy `ScoredPairProvider`.

**E2E or UI Workflow:**

- Sampling-driven practice-session assembly lives in consuming modules/workflows rather than here.

**Operational or Non-Functional:**

- Statistical sanity checks confirm non-positive-score items dominate sampling under the default weight factor.

### Quality Automation Plan

#### Automated Coverage Matrix

| ID | Target | Verification Level | Check or Test to Add | When It Runs | Notes |
| --- | --- | --- | --- | --- | --- |
| QA-1 | FR-2 | Unit | Without-replacement and statistical-weighting tests | PR CI | Guards the core policy. |
| QA-2 | FR-4 | Unit | Multi-exercise aggregation tests | PR CI | Protects pessimistic min-score behavior. |
| QA-3 | FR-6 | Contract | Protocol-conformance tests for injected providers | PR CI | Keeps provider injection stable. |

#### Static Checks and Gates

| ID | Check | Purpose | Trigger | Fails On |
| --- | --- | --- | --- | --- |
| SC-1 | Package static checks via package check | Preserve package quality. | PR CI | Lint or dead-code failures. |
| SC-2 | Package unit tests | Preserve weighting and adversarial behavior. | PR CI | Sampling regressions. |

#### Manual Verification Needed

| Target | Why It Is Not Reliably Automated | Manual Verification Approach | Evidence |
| --- | --- | --- | --- |
| Practice quality of the weighting policy | Statistical checks do not prove the pedagogical usefulness of the policy. | Review sampled sessions with realistic user score distributions. | Reviewer notes or exploratory scripts. |

### Risks

| ID | Risk | Impact | Mitigation or Next Step |
| --- | --- | --- | --- |
| RISK-1 | The v1 weighting rule may be too simplistic as user progress data grows. | Practice sessions could become less effective than intended. | Keep the strategy isolated so it can be replaced without API churn. |
| RISK-2 | The provider boundary may drift if consumers start assuming one concrete backend. | Cache or DB swaps become harder later. | Keep tests around protocol conformance and injected-store behavior. |

### Open Questions

| ID | Question | Status | Owner or Next Step | Notes |
| --- | --- | --- | --- | --- |
| OQ-1 | When should `sampling` prefer `database_cache` by default instead of building `ExerciseProgressStore` directly? | Open | Decide when cache behavior is considered stable enough for the hot path | Protocol support already makes this feasible. |

### Assumption Review Outcomes

| ID | Source | User Response | Outcome | Promoted To |
| --- | --- | --- | --- | --- |
| RV-1 | A-1 | Not yet reviewed | Kept as active assumption | A-1 |
| RV-2 | A-2 | Not yet reviewed | Kept as active assumption | A-2 |

### Open Question Resolution

| ID | Source | Resolution Status | Outcome | Promoted To or Next Step |
| --- | --- | --- | --- | --- |
| RV-3 | OQ-1 | Unresolved | Remains open pending hot-path architecture decisions | Revisit if `database_cache` becomes the default provider |

### Deferred Work

- D-1: Introduce richer sampling policies only when the simple sign-based rule is proven insufficient.
- D-2: Revisit default provider selection after `database_cache` adoption decisions.
