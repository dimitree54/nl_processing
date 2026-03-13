"""SQL query templates for detailed word operations.

Table names are formatted from Language enum values (e.g., "nl", "ru") —
controlled strings, never user input. Lines with table name formatting
use ``# noqa: S608`` to acknowledge the ruff S608 check.
"""


def create_word_details_table(src: str, tgt: str) -> str:
    """Create word_details table for a language pair."""
    # Table names from Language enum values, not user input  # noqa: S608
    return f"""
        CREATE TABLE IF NOT EXISTS word_details_{src}_{tgt} (
            id SERIAL PRIMARY KEY,
            source_word_id INTEGER NOT NULL REFERENCES words_{src}(id),
            word_type VARCHAR NOT NULL,
            schema_key VARCHAR NOT NULL,
            schema_version INTEGER NOT NULL,
            payload JSONB NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(source_word_id, word_type)
        )
    """  # noqa: S608


def upsert_word_details_query(table: str) -> str:
    """Upsert detailed word record query."""
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        INSERT INTO {table} (source_word_id, word_type, schema_key, schema_version, payload, updated_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (source_word_id, word_type) 
        DO UPDATE SET
            schema_key = EXCLUDED.schema_key,
            schema_version = EXCLUDED.schema_version,
            payload = EXCLUDED.payload,
            updated_at = NOW()
    """  # noqa: S608


def get_word_details_query(table: str) -> str:
    """Get detailed word record by source_word_id and word_type."""
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT source_word_id, word_type, schema_key, schema_version, payload
        FROM {table}
        WHERE source_word_id = $1 AND word_type = $2
    """  # noqa: S608


def get_word_details_batch_query(table: str, count: int) -> str:
    """Get detailed word records for multiple (source_word_id, word_type) pairs."""
    if count <= 0:
        msg = "Count must be positive"
        raise ValueError(msg)

    placeholders = ", ".join(f"(${i * 2 + 1}, ${i * 2 + 2})" for i in range(count))
    # Table name from Language enum values, not user input  # noqa: S608
    return f"""
        SELECT source_word_id, word_type, schema_key, schema_version, payload
        FROM {table}
        WHERE (source_word_id, word_type) IN ({placeholders})
    """  # noqa: S608
