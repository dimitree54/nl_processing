"""DetailedWordRecord model for persisting detailed word extraction data."""

from typing import Any

from pydantic import BaseModel


class DetailedWordRecord(BaseModel):
    """Detailed word extraction record for persistence.

    Represents the result of detailed extraction for a single word, containing
    the source word reference, schema metadata, and the extracted payload.
    """

    source_word: str
    word_type: str
    schema_key: str
    schema_version: int
    payload: dict[str, Any]
