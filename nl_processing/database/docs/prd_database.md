---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-02b-vision', 'step-02c-executive-summary', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments: ['product-brief-database-2026-03-02.md']
parentPrd: docs/planning-artifacts/prd.md
workflowType: 'prd'
classification:
  projectType: developer_tool
  domain: scientific
  complexity: medium
  projectContext: greenfield
---

# Product Requirements Document - database

**Author:** Dima
**Date:** 2026-03-07

> For shared requirements (structured output, configuration, language support, error handling, NFRs), see the [shared PRD](../../../docs/planning-artifacts/prd.md). This document covers only module-specific requirements.

## Executive Summary

`database` is the authoritative remote persistence module for `nl_processing`. It stores the shared word corpus, translation links, per-user word membership, and per-user exercise statistics in Neon PostgreSQL.

The module is optimized for **durability, relational correctness, and clean remote synchronization semantics**. It is not responsible for interactive low-latency access. That concern moves to the planned `database_cache` module, which will keep local snapshots and synchronize with `database` in the background.

Exercise statistics are modeled as **multiple dedicated tables**, one table per language pair and per exercise type. The exercise set is part of `ExerciseProgressStore` initialization, so callers work with an explicitly declared group of exercises instead of an implicit free-form namespace.

### What Makes This Special

- **Shared remote source of truth** for the whole vocabulary pipeline
- **Separated progress tables per exercise** instead of mixing all exercise types in one table
- **Fire-and-forget translation** coupled to persistence of newly added words
- **Cache-facing internal APIs** for snapshot export and idempotent increment replay

## Success Criteria

### Technical Success

- Shared corpus deduplication is correct
- Translation links point to the right source and target words
- User word lists reflect only that user's vocabulary membership
- Each configured exercise type persists into its own dedicated statistics table
- Background translation does not block `add_words()`
- Internal export / idempotent-apply APIs are sufficient for `database_cache`

### Measurable Outcomes

| Metric | Target | Measurement |
|---|---|---|
| Deduplication correctness | 100% | Integration / e2e assertions |
| Translation link accuracy | 100% | Integration / e2e assertions |
| Exercise table isolation | 100% | Table-level assertions per exercise |
| Async translation | Non-blocking return | Timing test around `add_words()` |
| Cache sync safety | No duplicate remote score application for the same event ID | Integration assertions |

## Scope

All features described here are required. `database` remains the canonical remote system of record.

**Risk Mitigation:**

- **Remote latency:** interactive latency is explicitly delegated to `database_cache`; `database` focuses on durable correctness and batch-friendly APIs.
- **Exercise proliferation:** exercise types are declared during store initialization so schema ownership is explicit and tables remain discoverable.
- **Async translation failures:** failures are logged and do not break the caller's successful write path.

## User Journeys

### Journey 1: Persist New Vocabulary

Alex extracts Dutch words from text and wants them stored durably. He instantiates `DatabaseService(user_id="alex")`, calls `add_words()`, and immediately gets `AddWordsResult` with `new_words` and `existing_words`. Background translation later creates the corresponding Russian words and translation links.

### Journey 2: Read Durable Word Pairs

Alex calls `get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)` and gets translated `WordPair` items from the authoritative remote store. This is useful for correctness checks, initial syncs, and non-hot-path backoffice flows.

### Journey 3: Track Multiple Exercises Separately

Alex configures progress storage with `exercise_types=["nl_to_ru", "multiple_choice", "listen_and_type"]`. Each exercise type has its own dedicated remote score table. A correct answer in one exercise never overwrites or reuses the score table of another exercise.

### Journey 4: Support Local Cache Synchronization

`database_cache` periodically refreshes a user's remote snapshot and replays queued local score events. It calls internal `database` APIs to:

1. export translated word pairs with stable remote IDs;
2. export scores for the configured exercise set;
3. apply score deltas idempotently using event IDs.

## Developer Tool Specific Requirements

### API Surface

**Public interface:**

```python
from nl_processing.database.service import DatabaseService
from nl_processing.core.models import Language, PartOfSpeech, Word

await DatabaseService.create_tables()

db = DatabaseService(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
)

result = await db.add_words(
    [
        Word(normalized_form="fiets", word_type=PartOfSpeech.NOUN, language=Language.NL),
        Word(normalized_form="lopen", word_type=PartOfSpeech.VERB, language=Language.NL),
    ]
)

pairs = await db.get_words(word_type=PartOfSpeech.NOUN, limit=10, random=True)
```

**Internal exercise-progress interface:**

```python
from nl_processing.database.exercise_progress import ExerciseProgressStore
from nl_processing.core.models import Language

progress = ExerciseProgressStore(
    user_id="alex",
    source_language=Language.NL,
    target_language=Language.RU,
    exercise_types=["nl_to_ru", "multiple_choice"],
)

await progress.increment(
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,
)

scored_pairs = await progress.get_word_pairs_with_scores()
```

**Internal cache-support interface:**

```python
snapshot = await progress.export_remote_snapshot()
await progress.apply_score_delta(
    event_id="0b4434bb-5d9f-4d38-aace-4eabf2c73460",
    source_word_id=101,
    exercise_type="nl_to_ru",
    delta=-1,
)
```

**Exceptions** (module-specific):

- `ConfigurationError` — required configuration missing or invalid
- `DatabaseError` — remote persistence / query failures

### Implementation Considerations

- `Word` from `core.models` remains the canonical word shape
- `database` owns remote durability and canonical IDs
- exercise tables are created per language pair and per exercise type
- the configured exercise set is part of `ExerciseProgressStore` initialization
- `database_cache` consumes internal export / replay APIs; `database` does not do local caching itself

## Functional Requirements

### Database Setup

- FR1: Module provides `create_tables()` async class method creating all required remote tables.
- FR2: Module creates per-language word tables (for example `words_nl`, `words_ru`) with `id`, `normalized_form`, and `word_type`.
- FR3: Module creates per-language-pair translation link tables (for example `translations_nl_ru`).
- FR4: Module creates per-user word membership tables referencing the shared language tables.

### Word Management

- FR5: `add_words(words: list[Word])` adds new words to the proper language table based on `Word.language`.
- FR6: Duplicate words are detected by normalized form and are not re-inserted.
- FR7: `add_words()` returns `AddWordsResult(new_words, existing_words)`.
- FR8: All provided words are associated with the current user.
- FR9: New words trigger asynchronous translation through `translate_word`.
- FR10: Completed translations are written to the target-language table and linked through the translation table.

### Word Retrieval

- FR11: `get_words()` returns `list[WordPair]` for the current user and configured language pair.
- FR12: Words without completed translations are excluded from `get_words()` results.
- FR13: `get_words()` accepts optional `word_type` filtering.
- FR14: `get_words()` accepts optional `limit`.
- FR15: `get_words()` accepts optional `random` sampling for remote retrieval scenarios.

### Configuration

- FR16: Module requires `DATABASE_URL`.
- FR17: Missing `DATABASE_URL` raises `ConfigurationError` at instantiation time.
- FR18: `DatabaseService` accepts `source_language` and `target_language` (defaults: `Language.NL`, `Language.RU`).

### Logging

- FR19: Module uses structured logging.
- FR20: Translation failures are logged without failing the caller's completed `add_words()` operation.
- FR21: Missing translations excluded from reads are logged as warnings.

### Testing Utilities

- FR22: Module provides `drop_all_tables()` for test teardown.
- FR23: Module provides `reset_database()` for clean test setup.
- FR24: Module provides count helpers for assertions.
- FR25: Test utilities live in `testing.py` and are never imported by production modules.
- FR26: `create_tables()` uses idempotent `IF NOT EXISTS` semantics.

### Exercise Progress Tracking

- FR27: Module creates one score table per language pair and per exercise type.
- FR28: Table naming follows `user_word_exercise_scores_<src>_<tgt>_<exercise_slug>`.
- FR29: `ExerciseProgressStore` constructor accepts `exercise_types: list[str]` and requires a non-empty list.
- FR30: `ExerciseProgressStore.increment(...)` validates that `exercise_type` belongs to the configured set.
- FR31: Each increment updates only the dedicated table for that exercise type.
- FR32: `delta` is limited to `+1` or `-1`.
- FR33: Missing score is treated as `0` during reads.
- FR34: `get_word_pairs_with_scores()` returns translated `WordPair` items plus scores for all configured exercise types.
- FR35: Exercise scores are per-user only and never modify shared corpus rows.

### Cache Support

- FR36: Module exposes an internal snapshot export returning translated word pairs with stable remote IDs.
- FR37: Snapshot export includes scores for all exercise types configured in the `ExerciseProgressStore`.
- FR38: Module exposes an internal `apply_score_delta(event_id, ...)` operation for cache replay.
- FR39: `event_id` is treated as an idempotency key.
- FR40: Repeating the same `event_id` must not double-apply the remote score delta.

## Non-Functional Requirements (Module-Specific)

### Performance

- NFR1: `database` is optimized for durable remote correctness, not for interactive sub-200ms user-facing reads.
- NFR2: Batch operations should use database-native batching where practical.
- NFR3: Snapshot export and idempotent delta apply must be efficient enough for background cache refresh / flush jobs.

### Async

- NFR4: All public and cache-support methods are async.
- NFR5: Translation spawned by `add_words()` runs in the background.
- NFR6: Background failures are logged, not leaked to unrelated callers.

### Reliability

- NFR7: Remote connectivity failures surface as `DatabaseError`.
- NFR8: `database` remains the canonical source of truth even when caches are stale or unavailable.
- NFR9: Idempotent score replay guarantees safe retries from `database_cache`.

### Testing

- NFR10: Integration and e2e tests run against a real Neon database in the Doppler `dev` environment.
- NFR11: Tests verify per-exercise table creation and isolation.
- NFR12: Tests verify idempotent replay with repeated event IDs.
- NFR13: Tests leave the dev database clean after completion.

### Module-Specific Dependencies

- NFR14: `asyncpg` for Neon connectivity
- NFR15: `translate_word` for background translation
