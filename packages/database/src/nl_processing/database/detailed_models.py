"""DetailedWordRecord model for persisting detailed word extraction data."""

from pydantic import BaseModel

# Expanded payload type that supports more nesting levels
JsonValue = (
    str
    | int
    | float
    | bool
    | None
    | list[str]
    | list[int]
    | list[dict[str, str | int | None]]
    | dict[str, str]
    | dict[str, int]
    | dict[str, bool]
    | dict[str, str | int | bool | None]
    | dict[str, list[str]]
    | dict[str, list[dict[str, str | None]]]
)


class DetailedWordRecord(BaseModel):
    """Detailed word extraction record for persistence.

    Represents the result of detailed extraction for a single word, containing
    the source word reference, schema metadata, and the extracted payload.
    """

    source_word: str
    word_type: str
    schema_key: str
    schema_version: int
    payload: dict[str, JsonValue]
