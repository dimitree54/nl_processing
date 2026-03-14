"""DDL and query constants for the tiered exercise cache store."""

DDL_TIERED_SNAPSHOT = """
CREATE TABLE IF NOT EXISTS tiered_cached_word_pairs (
    source_word_id INTEGER NOT NULL,
    source_normalized_form TEXT NOT NULL,
    source_word_type TEXT NOT NULL,
    target_word_id INTEGER NOT NULL,
    target_normalized_form TEXT NOT NULL,
    target_word_type TEXT NOT NULL,
    PRIMARY KEY (source_word_id)
)"""

DDL_TIERED_SCORES = """
CREATE TABLE IF NOT EXISTS tiered_cached_scores (
    source_word_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,
    score INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source_word_id, exercise_type)
)"""

DDL_TIERED_REPEAT_STATE = """
CREATE TABLE IF NOT EXISTS tiered_repeat_state (
    mode_slug TEXT NOT NULL,
    source_word_id INTEGER NOT NULL,
    activated_at TEXT NOT NULL,
    PRIMARY KEY (mode_slug, source_word_id)
)"""

DDL_TIERED_PENDING_EVENTS = """
CREATE TABLE IF NOT EXISTS tiered_pending_events (
    event_id TEXT PRIMARY KEY,
    mode_slug TEXT NOT NULL,
    source_word_id INTEGER NOT NULL,
    exercise_type TEXT NOT NULL,
    delta INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    flushed_at TEXT,
    last_error TEXT
)"""

DDL_TIERED_METADATA = """
CREATE TABLE IF NOT EXISTS tiered_cache_metadata (
    id INTEGER PRIMARY KEY DEFAULT 1,
    mode_slug TEXT NOT NULL,
    exercise_types TEXT NOT NULL,
    schema_version INTEGER NOT NULL DEFAULT 1,
    last_refresh_started_at TEXT,
    last_refresh_completed_at TEXT,
    last_flush_completed_at TEXT,
    last_error TEXT
)"""

ALL_TIERED_DDL = [
    DDL_TIERED_SNAPSHOT,
    DDL_TIERED_SCORES,
    DDL_TIERED_REPEAT_STATE,
    DDL_TIERED_PENDING_EVENTS,
    DDL_TIERED_METADATA,
]

UPSERT_TIERED_SCORE = (
    "INSERT INTO tiered_cached_scores (source_word_id, exercise_type, score, updated_at) VALUES (?, ?, ?, ?)"
    " ON CONFLICT(source_word_id, exercise_type) DO UPDATE SET score = score + ?, updated_at = ?"
)

INSERT_TIERED_WORD_PAIR = (
    "INSERT INTO tiered_cached_word_pairs "
    "(source_word_id, source_normalized_form, source_word_type, "
    "target_word_id, target_normalized_form, target_word_type) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)

INSERT_TIERED_PENDING_EVENT = (
    "INSERT INTO tiered_pending_events "
    "(event_id, mode_slug, source_word_id, exercise_type, delta, created_at) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)

INSERT_TIERED_REPEAT_STATE = (
    "INSERT INTO tiered_repeat_state (mode_slug, source_word_id, activated_at) VALUES (?, ?, ?)"
)

DELETE_TIERED_REPEAT_STATE = "DELETE FROM tiered_repeat_state WHERE mode_slug = ? AND source_word_id = ?"
