---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-03-04'
inputDocuments:
  - docs/planning-artifacts/product-brief.md
  - docs/planning-artifacts/prd.md
  - docs/planning-artifacts/architecture.md
  - nl_processing/sampling/docs/product-brief-sampling-2026-03-04.md
  - nl_processing/sampling/docs/prd_sampling.md
  - nl_processing/database/docs/architecture_database.md
workflowType: 'architecture'
project_name: 'nl_processing'
user_name: 'Dima'
date: '2026-03-04'
scope: 'sampling'
parentArchitecture: docs/planning-artifacts/architecture.md
---

# Architecture Decision Document — sampling

> For shared architectural decisions (core package, code style, patterns, project structure), see the [shared architecture](../../../docs/planning-artifacts/architecture.md). This document covers only module-specific decisions.

---

## Module-Specific Architectural Decisions

### Decision: Database Is the Source of Truth

`sampling` does not maintain its own state. It reads from a pluggable data source that provides:

- The user's translated word pairs
- The user's per-exercise integer scores

The data source can be remote DB (`ExerciseProgressStore`) or local cache (`DatabaseCacheService`).

**Rationale:** Sampling must reflect the latest persisted progress and must not diverge across processes. Keeping all progress state in the database makes sampling stateless and easy to scale. Data source pluggability allows faster sampling using local cache when appropriate.

### Decision: Exercise Types Are Stored as Stable Strings

Exercise types are represented as `str` identifiers (e.g., "nl_to_ru"). They are persisted as `VARCHAR` in the database scoring tables.

**Rationale:** New exercises should not require schema changes. Using strings avoids locking v1 into a fixed enum.

### Decision: Pessimistic Aggregation Across Exercises

When multiple `exercise_types` are requested, the sampler uses `min_score` across those exercises and applies the v1 weighting rule to that aggregate.

**Implication:** A word is treated as "mastered" (down-weighted) only if it is mastered across all requested exercises.

### Decision: Weighted Sampling Without Replacement

Sampling returns unique word pairs. Internally, the implementation should use a standard weighted-without-replacement algorithm.

**Rationale:** Quizzes should not repeat the same word in a single short session, and without-replacement behavior is the natural expectation for a sampling module.

### Decision: Adversarial Sampling by Part of Speech (Uniform)

For multiple-choice exercises, `sampling` provides an adversarial sampling helper that selects distractor words from the same user's dictionary that share the same part of speech (часть речи) as a provided word.

- Filter: `candidate.source.word_type == source_word.word_type`
- Exclude: the provided word itself (same normalized form)
- Sampling: uniform random without replacement (no weights)

**Rationale:** Multiple-choice options should be plausible. Matching part of speech yields distractors that are more likely to be confusing without requiring semantic similarity models in v1.

### Decision: Protocol-Based Data Source Injection

The sampler accepts an optional `scored_store` parameter conforming to `ScoredPairProvider` Protocol that requires only `get_word_pairs_with_scores() -> list[ScoredWordPair]`. When not provided, the sampler constructs `ExerciseProgressStore` as before (backward compatibility).

**Rationale:** Both `ExerciseProgressStore` (remote) and `DatabaseCacheService` (local cache) implement this method. Structural typing via Protocol avoids coupling the sampler to either concrete class. The Protocol is defined in `sampling/service.py` (co-located, since it's the only consumer).

---

## Module Internal Structure

```
nl_processing/sampling/
├── __init__.py              # empty
├── service.py               # WordSampler (public class), ScoredPairProvider (Protocol)
└── docs/
    ├── product-brief-sampling-2026-03-04.md
    ├── prd_sampling.md
    └── architecture_sampling.md  # THIS DOCUMENT
```

---

## Test Strategy

- **Unit tests:** Mock database access layer via `ScoredPairProvider` Protocol (which they already do via `MockProgressStore` — now formalized). Validate weight computation, aggregation across exercises, sampling without replacement, edge cases (empty candidates, limit <= 0).
- **Integration tests:** Use a real dev database populated with a small fixture set of user words + scores. Validate that sampled distribution responds to score sign.
