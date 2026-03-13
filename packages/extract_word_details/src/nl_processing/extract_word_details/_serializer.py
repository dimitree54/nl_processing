"""Serialization contract for detailed word models.

Provides round-trip serialization through the schema registry with
proper validation and error handling.
"""

from pydantic import BaseModel, ValidationError

from nl_processing.extract_word_details._exceptions import PayloadValidationError, SchemaVersionError
from nl_processing.extract_word_details._schema_registry import SchemaRegistry


def serialize_payload(record: BaseModel) -> dict[str, object]:
    """Serialize a Pydantic model to a dictionary payload.

    Args:
        record: The Pydantic model instance to serialize.

    Returns:
        Dictionary representation of the model.
    """
    return record.model_dump()


def parse_payload(
    schema_key: str, schema_version: int, payload: dict[str, object], registry: SchemaRegistry
) -> BaseModel:
    """Parse a payload dictionary into a Pydantic model.

    Args:
        schema_key: Schema key (e.g., "nl_ru_noun").
        schema_version: Schema version number.
        payload: Dictionary to deserialize.
        registry: Schema registry for model lookup.

    Returns:
        Validated Pydantic model instance.

    Raises:
        SchemaVersionError: If schema key or version is unknown.
        PayloadValidationError: If payload fails validation.
    """
    try:
        entry = registry.get_entry(schema_key, schema_version)
    except KeyError as e:
        raise SchemaVersionError(str(e)) from e

    try:
        return entry.model_class.model_validate(payload)
    except ValidationError as e:
        raise PayloadValidationError(f"Validation failed: {e}") from e
