"""SQL query templates for tiered exercise repeat-state management.

Table names are formatted from Language enum values (e.g., "nl", "ru") —
controlled strings, never user input. Lines with table name formatting
use ``# noqa: S608`` to acknowledge the ruff S608 check.
"""


def create_tiered_repeat_state_table(src: str, tgt: str) -> str:
    """Create repeat-state table DDL for tiered exercises."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS user_word_tiered_repeat_state_{src}_{tgt} (
            user_id VARCHAR NOT NULL,
            mode_slug VARCHAR NOT NULL,
            source_word_id INTEGER NOT NULL,
            activated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, mode_slug, source_word_id)
        )
    """  # noqa: S608


def upsert_repeat_state(src: str, tgt: str) -> str:
    """Insert repeat-state row (idempotent activation)."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        INSERT INTO user_word_tiered_repeat_state_{src}_{tgt} 
            (user_id, mode_slug, source_word_id, activated_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (user_id, mode_slug, source_word_id) DO NOTHING
    """  # noqa: S608


def delete_repeat_state(src: str, tgt: str) -> str:
    """Delete repeat-state row by (user_id, mode_slug, source_word_id)."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        DELETE FROM user_word_tiered_repeat_state_{src}_{tgt}
        WHERE user_id = $1 AND mode_slug = $2 AND source_word_id = $3
    """  # noqa: S608


def get_repeat_states(src: str, tgt: str) -> str:
    """Select all repeat-state rows for a user and mode_slug."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT user_id, mode_slug, source_word_id, activated_at
        FROM user_word_tiered_repeat_state_{src}_{tgt}
        WHERE user_id = $1 AND mode_slug = $2
    """  # noqa: S608


def get_repeat_state(src: str, tgt: str) -> str:
    """Select one repeat-state row for a (user_id, mode_slug, source_word_id)."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT user_id, mode_slug, source_word_id, activated_at
        FROM user_word_tiered_repeat_state_{src}_{tgt}
        WHERE user_id = $1 AND mode_slug = $2 AND source_word_id = $3
    """  # noqa: S608
